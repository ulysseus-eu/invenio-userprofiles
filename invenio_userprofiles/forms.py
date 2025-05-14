# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2018 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Forms for user profiles."""

import pytz
from flask import current_app
from flask_login import current_user
from flask_security.forms import email_required, email_validator, unique_user_email
from flask_wtf import FlaskForm
from invenio_i18n import lazy_gettext as _
from invenio_i18n.ext import InvenioI18N
from werkzeug.local import LocalProxy
from wtforms import (
    FormField,
    RadioField,
    SelectField,
    StringField,
    SubmitField,
    validators,
    BooleanField
)
from wtforms.validators import (
    DataRequired,
    EqualTo,
    Length,
    StopValidation,
    ValidationError,
)

from .models import UserProfileProxy
from .validators import USERNAME_RULES, validate_username


def strip_filter(text):
    """Filter for trimming whitespace.

    :param text: The text to strip.
    :returns: The stripped text.
    """
    return text.strip() if text else text


def current_user_email(form, field):
    """Field validator to stop validation if email wasn't changed."""
    if current_user.email.lower() == field.data.lower():
        raise StopValidation()


class ProfileForm(FlaskForm):
    """Form for editing user profile."""

    profile_proxy_cls = UserProfileProxy

    username = StringField(
        # NOTE: Form field label
        _("Username"),
        # NOTE: Form field help text
        description=_("Required. {username_rules}").format(
            username_rules=USERNAME_RULES
        ),
        validators=[Length(max=50), DataRequired(message=_("Username not provided."))],
        filters=[strip_filter],
    )

    full_name = StringField(
        # NOTE: Form label
        _("Full name"),
        validators=[Length(max=255)],
        filters=[strip_filter],
    )

    affiliations = StringField(
        # NOTE: Form label
        _("Affiliations"),
        validators=[Length(max=255)],
        filters=[strip_filter],
    )
    
    profile_genre = StringField(filters=[strip_filter])
    profile_university = StringField(filters=[strip_filter])
    profile_links = StringField(filters=[strip_filter])
    profile_languages =  StringField(filters=[strip_filter])
    profile_identify =  StringField(filters=[strip_filter])
    profile_faculty =  StringField(filters=[strip_filter])
    profile_department = StringField(filters=[strip_filter])
    profile_career_stage =  StringField(filters=[strip_filter])
    profile_research_group = BooleanField()
    profile_keywords = StringField(filters=[strip_filter])
    profile_expertise_1 = StringField(filters=[strip_filter])
    profile_expertise_2 = StringField(filters=[strip_filter])
    profile_research_area =  StringField(filters=[strip_filter])
    profile_if_not_please_state_the_full_name_of_the_principal_investigator_of_your_research_group_please_use_this_format_first_name_last_name =  BooleanField()
    profile_if_not_please_state_the_full_name_of_the_principal_investigator_of_your_research_group_please_use_this_format_first_name_last_name_write_name =  StringField(filters=[strip_filter])
    
    # profile projects tabs
    projects_have_you_ever_designed_or_written_a_european_project_proposal = BooleanField()
    projects_have_you_ever_participated_in_a_granted_european_project_as_consortium_leader = BooleanField()
    projects_have_you_ever_participated_in_a_granted_european_project_as_a_member_of_consortium =BooleanField()
    projects_have_you_been_an_evaluator_of_eu_projects = BooleanField()
    projects_has_your_research_resulted_in_a_knowledge_transfer_initiative =BooleanField()
    projects_if_yes_please_name_the_project_s_you_have_coordinated_including_the_corresponding_call_s = StringField(filters=[strip_filter])
    projects_i_have_founded_a_spin_off_company_as_a_result_of_my_research = BooleanField()
    projects_i_am_a_member_of_a_spin_off_company_linked_to_my_university= BooleanField()
    projects_i_have_patented_the_results_of_my_research= BooleanField()
    projects_i_am_an_active_member_of_a_business_chair_linked_to_my_university= BooleanField()
    projects_are_you_the_principal_investigator_of_your_research_group= BooleanField()
    profile_please_indicate_the_full_name_of_your_research_group_in_english=StringField(filters=[strip_filter])
    projects_other = BooleanField()
    projects_other_response = StringField(filters=[strip_filter])
    projects_affiliated_relevant_associations_platforms_clusters = StringField(filters=[strip_filter])
    
    # profile research_groups tabs
    research_group_are_you_interested_in_participating_in_building_joint_research_groups_centered_around_shared_research_disciplines_within_ulysseus_partner_universities = BooleanField()
    research_group_most_relevant_to_your_research = StringField(filters=[strip_filter])
    research_group_information_on_the_most_significant_projects = StringField(filters=[strip_filter])
    
    # profile consent tabs
    consent_by_providing_my_consent =BooleanField()
    consent_profile_privacy_level =BooleanField()

    def validate_username(self, field):
        """Wrap username validator for WTForms."""
        try:
            validate_username(field.data)
        except ValueError as e:
            raise ValidationError(e)

        # Check if username is already taken.
        datastore = current_app.extensions["security"].datastore
        user = datastore.find_user(username=field.data)
        if user is None:
            return

        # NOTE: Form validation error.
        msg = _("Username is not available.")

        if current_user.is_anonymous:
            # We are handling a new sign up (i.e. anonymous user) AND a
            # the username already exists. Fail.
            raise ValidationError(msg)
        else:
            # We are handling a user editing their profile AND a
            # the username already exists.
            is_same_user = current_user.get_id() == str(user.id)
            if not is_same_user:
                # Username already taken by another user.
                raise ValidationError(msg)

    def process(self, formdata=None, obj=None, data=None, extra_filters=None, **kwargs):
        """Build a proxy around the object."""
        if obj is not None:
            obj = self.profile_proxy_cls(obj)
        super().process(
            formdata=formdata, obj=obj, data=data, extra_filters=extra_filters, **kwargs
        )

    def populate_obj(self, user):
        """Populates the obj."""
        user = self.profile_proxy_cls(user)
        super().populate_obj(user)


class EmailProfileForm(ProfileForm):
    """Form to allow editing of email address."""

    email = StringField(
        # NOTE: Form field label
        _("Email address"),
        filters=[
            lambda x: x.lower() if x is not None else x,
        ],
        validators=[
            email_required,
            current_user_email,
            email_validator,
            unique_user_email,
        ],
    )

    email_repeat = StringField(
        # NOTE: Form field label
        _("Re-enter email address"),
        # NOTE: Form field help text
        description=_("Please re-enter your email address."),
        filters=[
            lambda x: x.lower() if x else x,
        ],
        validators=[
            email_required,
            # NOTE: Form validation error.
            EqualTo("email", message=_("Email addresses do not match.")),
        ],
    )


class VerificationForm(FlaskForm):
    """Form to render a button to request email confirmation."""

    # NOTE: Form button label
    send_verification_email = SubmitField(_("Resend verification email"))


def register_form_factory(Form):
    """Factory for creating an extended user registration form."""

    class CsrfDisabledProfileForm(ProfileForm):
        """Subclass of ProfileForm to disable CSRF token in the inner form.

        This class will always be a inner form field of the parent class
        `Form`. The parent will add/remove the CSRF token in the form.
        """

        def __init__(self, *args, **kwargs):
            """Initialize the object by hardcoding CSRF token to false."""
            kwargs = _update_with_csrf_disabled(kwargs)
            super(CsrfDisabledProfileForm, self).__init__(*args, **kwargs)

    class RegisterForm(Form):
        """RegisterForm extended with UserProfile details."""

        # cannot be called `user_profile`, to avoid naming collision with the
        # hybrid property in the model
        profile = FormField(CsrfDisabledProfileForm, separator=".")

        def to_dict(self):
            profile_data = self.profile.data
            data = super().to_dict()
            data["username"] = profile_data.pop("username")
            data["user_profile"] = profile_data
            return data

    return RegisterForm


class PreferencesForm(FlaskForm):
    """Form for editing user profile."""

    profile_proxy_cls = UserProfileProxy

    visibility = RadioField(
        _("Profile visibility"),
        choices=[
            ("public", _("Public")),
            ("restricted", _("Hidden")),
        ],
        description=_(
            "Public profiles can be found by other users via searches on "
            "username, full name and affiliation. Hidden profiles cannot be"
            " found by other users."
        ),
    )

    email_visibility = RadioField(
        _("Email visibility"),
        choices=[
            ("public", _("Public")),
            ("restricted", _("Hidden")),
        ],
        description=_(
            "Public email visibility enables your profile to be found by "
            "your email address."
        ),
    )

    locale = LocalProxy(
        lambda: SelectField(
            _("Preferences locale"),
            choices=set(current_app.extensions["invenio-i18n"].get_locales()),
        ),
    )

    # timezone = SelectField(
    #    _("Preferences timezone"),
    #    choices=pytz.all_timezones,
    #    validators=[validators.InputRequired()],
    # )

    def process(self, formdata=None, obj=None, data=None, extra_filters=None, **kwargs):
        """Build a proxy around the object."""
        if obj is not None:
            obj = self.profile_proxy_cls(obj)
        super().process(
            formdata=formdata, obj=obj, data=data, extra_filters=extra_filters, **kwargs
        )

    def populate_obj(self, user):
        """Populates the obj."""
        user = self.profile_proxy_cls(user)
        super().populate_obj(user)


def confirm_register_form_factory(Form):
    """Factory for creating a confirm register form with UserProfile fields."""

    class CsrfDisabledProfileForm(ProfileForm):
        """Subclass of ProfileForm to disable CSRF token in the inner form.

        This class will always be an inner form field of the parent class
        `Form`. The parent will add/remove the CSRF token in the form.
        """

        def __init__(self, *args, **kwargs):
            """Initialize the object by hardcoding CSRF token to false."""
            kwargs = _update_with_csrf_disabled(kwargs)
            super().__init__(*args, **kwargs)

    class ConfirmRegisterForm(Form):
        """RegisterForm extended with UserProfile details."""

        # cannot be called `user_profile`, to avoid naming collision with the
        # hybrid property in the model
        profile = FormField(CsrfDisabledProfileForm, separator=".")

        def to_dict(self):
            profile_data = self.profile.data
            data = super().to_dict()
            data["username"] = profile_data.pop("username")
            data["user_profile"] = profile_data
            return data

    return ConfirmRegisterForm


def confirm_register_form_preferences_factory(Form):
    """Factory for creating a confirm register form with UserProfile and Preferences."""

    class CsrfDisabledPreferencesForm(PreferencesForm):
        """Subclass of PreferencesForm to disable CSRF token in the inner form."""

        def __init__(self, *args, **kwargs):
            """Initialize the object by hardcoding CSRF token to false."""
            kwargs = _update_with_csrf_disabled(kwargs)
            super().__init__(*args, **kwargs)

    class ConfirmRegisterForm(Form):
        """RegisterForm extended with Preferences details."""

        # cannot be called `preferences`, to avoid naming collision with the
        # hybrid property in the model
        prefs = FormField(CsrfDisabledPreferencesForm, separator=".")

        def to_dict(self):
            preferences_data = self.prefs.data
            data = super().to_dict()
            data["preferences"] = preferences_data
            return data

    return ConfirmRegisterForm


def _update_with_csrf_disabled(d=None):
    """Update the input dict with CSRF disabled."""
    if d is None:
        d = {}
    d.setdefault("meta", {})
    d["meta"].update({"csrf": False})
    return d
