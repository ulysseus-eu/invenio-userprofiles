# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2018 CERN.
# Copyright (C) 2022 Northwestern University.
# Copyright (C) 2023-2024 Graz University of Technology.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Invenio module that adds userprofiles to the platform."""
from warnings import warn

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from flask_security.confirmable import send_confirmation_instructions
from invenio_db import db
from invenio_records_resources.services.uow import TaskOp, unit_of_work
from invenio_i18n import lazy_gettext as _
from .tasks import execute_user_profile_update_actions

from .forms import EmailProfileForm, PreferencesForm, ProfileForm, VerificationForm
from .models import UserProfileProxy


def create_blueprint(app):
    """Create blueprint."""
    blueprint = Blueprint(
        "invenio_userprofiles",
        __name__,
        template_folder="templates",
        url_prefix="/account/settings",
    )

    @blueprint.app_template_filter()
    def userprofile(value):
        """Retrieve user profile for a given user id."""
        warn("userprofile template filter is deprecated.", DeprecationWarning)
        return UserProfileProxy.get_by_userid(int(value))

    blueprint.add_url_rule("/profile", view_func=profile, methods=["GET", "POST"])
    blueprint.add_url_rule("/preferences", view_func=preferences, methods=["GET", "POST"])

    return blueprint


@login_required
def profile():
    """View for editing a profile."""
    # Create forms
    verification_form = VerificationForm(formdata=None, prefix="verification")
    profile_form = profile_form_factory()

    # Pick form
    is_read_only = current_app.config.get("USERPROFILES_READ_ONLY", False)
    form_name = request.form.get("submit", None)
    if form_name == "profile" and not is_read_only:
        handle_form = handle_profile_form
        form = profile_form
    elif form_name == "verification":
        handle_form = handle_verification_form
        form = verification_form
    else:
        form = None

    # Process form
    if form:
        form.process(formdata=request.form)
        if form.validate_on_submit():
            handle_form(form)
            return redirect(url_for(".profile"), code=303)  # this endpoint

    return render_template(
        current_app.config["USERPROFILES_PROFILE_TEMPLATE"],
        verification_form=verification_form,
        profile_form=profile_form,
    )


@login_required
def preferences():
    """View for editing preferences."""
    # Create forms
    preferences_form = PreferencesForm(
        formdata=None, obj=current_user, prefix="preferences"
    )

    # Pick form
    is_read_only = current_app.config.get("USERPROFILES_READ_ONLY", False)
    form_name = request.form.get("submit", None)
    if form_name == "preferences":
        handle_form = handle_preferences_form
        form = preferences_form
    else:
        form = None

    # Process form
    if form:
        form.process(formdata=request.form)
        if form.validate_on_submit():
            handle_form(form)
            return redirect(url_for(".preferences"), code=303)  # this endpoint

    return render_template(
        current_app.config["USERPROFILES_PREFERENCES_TEMPLATE"],
        preferences_form=preferences_form,
    )


def profile_form_factory():
    """Create a profile form."""
    if current_app.config["USERPROFILES_EMAIL_ENABLED"]:
        return EmailProfileForm(
            formdata=None,
            obj=current_user,
            prefix="profile",
        )
    else:
        return ProfileForm(
            formdata=None,
            obj=current_user,
            prefix="profile",
        )


def handle_verification_form(form):
    """Handle email sending verification form."""
    send_confirmation_instructions(current_user)
    # NOTE: Flash message.
    flash(_("Verification email sent."), category="success")


@unit_of_work()
def handle_profile_form(form, uow=None):
    """Handle profile update form."""
    email_changed = False
    datastore = current_app.extensions["security"].datastore
    with db.session.begin_nested():
        if (
            current_app.config["USERPROFILES_EMAIL_ENABLED"]
            and form.email.data.lower() != current_user.email.lower()
        ):
            email_changed = True
        form.populate_obj(current_user)
        db.session.add(current_user)
        datastore.mark_changed(id(db.session), uid=current_user.id)
    datastore.commit()
    uow.register(TaskOp(execute_user_profile_update_actions, user_id=current_user.id, action="update_owned_persons"))

    if email_changed:
        send_confirmation_instructions(current_user)
        # NOTE: Flash message after successful update of profile.
        flash(
            _(
                "Profile was updated. We have sent a verification "
                "email to %(email)s. Please check it.",
                email=current_user.email.lower(),
            ),
            category="success",
        )
    else:
        # NOTE: Flash message after successful update of profile.
        flash(_("Profile was updated."), category="success")


@unit_of_work()
def handle_preferences_form(form, uow=None):
    """Handle preferences form."""
    form.populate_obj(current_user)
    db.session.add(current_user)
    current_app.extensions["security"].datastore.commit()
    uow.register(TaskOp(execute_user_profile_update_actions, user_id=current_user.id, action="update_owned_persons"))
    # NOTE: Flash message after successful update of profile.
    flash(_("Preferences were updated."), category="success")
