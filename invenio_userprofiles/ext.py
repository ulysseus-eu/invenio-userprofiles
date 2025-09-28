# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2018 CERN.
# Copyright (C) 2024 Graz University of Technology.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""User profiles module for Invenio."""

import importlib.metadata as m
from sys import version_info

from flask_menu import current_menu
from invenio_i18n import LazyString
from invenio_i18n import lazy_gettext as _
from invenio_theme.proxies import current_theme_icons

from . import config
from .api import current_userprofile
from .forms import confirm_register_form_factory, register_form_factory


def entry_points(group):
    """Entry points."""
    if version_info < (3, 10):
        eps = m.entry_points()
        # the only reason to add this check is to simplify the tests! the tests
        # are implemented against python >=3.10 which uses the group keyword.
        # since we drop python3.9 soon, this should work!
        # in the tests there is a line which patches the return value of
        # importlib.metadata.entry_points with a list. this works for
        # python>=3.10 but not for 3.9
        # the return value of .get can contain duplicates. the simplest way to
        # remove is the set() call, to still return a list, list() is called on
        # set()
        if isinstance(eps, dict):
            eps = list(set(eps.get(group, [])))
    else:
        eps = m.entry_points(group=group)

    return eps


def _register_entry_point(registry, ep_name):
    """Load entry points into the given registry."""
    for ep in entry_points(group=ep_name):
        # Entry point has the action as the name (e.g. invenio_users_resources.moderation.actions.block = ... , 'block' is the name)
        action_name = ep.name
        action = ep.load()
        assert callable(action)
        registry.setdefault(action_name, []).append(action)


class InvenioUserProfiles(object):
    """Invenio-UserProfiles extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization."""
        self.init_config(app)

        # Register current_profile
        app.context_processor(lambda: dict(current_userprofile=current_userprofile))
        self.init_actions_registry()
        app.extensions["invenio-userprofiles"] = self

    def init_config(self, app):
        """Initialize configuration."""
        excludes = [
            "USERPROFILES_BASE_TEMPLATE",
            "USERPROFILES_SETTINGS_TEMPLATE",
        ]
        for k in dir(config):
            if k.startswith("USERPROFILES_") and k not in excludes:
                app.config.setdefault(k, getattr(config, k))

        app.config.setdefault("USERPROFILES", True)

        app.config.setdefault(
            "USERPROFILES_BASE_TEMPLATE",
            app.config.get("BASE_TEMPLATE", "invenio_userprofiles/base.html"),
        )

        app.config.setdefault(
            "USERPROFILES_SETTINGS_TEMPLATE",
            app.config.get(
                "SETTINGS_TEMPLATE", "invenio_userprofiles/settings/base.html"
            ),
        )

        if app.config["USERPROFILES_EXTEND_SECURITY_FORMS"]:
            app.config.setdefault(
                "USERPROFILES_REGISTER_USER_BASE_TEMPLATE",
                app.config.get(
                    "SECURITY_REGISTER_USER_TEMPLATE",
                    "invenio_accounts/register_user.html",
                ),
            )

            app.config["SECURITY_REGISTER_USER_TEMPLATE"] = (
                "invenio_userprofiles/register_user.html"
            )

    def init_actions_registry(self):
        """Initialises moderation actions registry."""
        self.actions_registry = {}
        _register_entry_point(
            self.actions_registry,
            "invenio_userprofiles.profile_update.actions",
        )


def finalize_app(app):
    """Finalize app.

    NOTE: replace former @record_once decorator
    """
    init_common(app)
    init_menu(app)


def api_finalize_app(app):
    """Finalize app for api.

    NOTE: replace former @record_once decorator
    """
    init_common(app)


def init_common(app):
    """Post initialization."""
    if app.config["USERPROFILES_EXTEND_SECURITY_FORMS"]:
        security_ext = app.extensions["security"]
        security_ext.confirm_register_form = confirm_register_form_factory(
            security_ext.confirm_register_form
        )
        security_ext.register_form = register_form_factory(security_ext.register_form)


def init_menu(app):
    """Init menu."""
    current_menu.submenu("settings.profile").register(
        endpoint="invenio_userprofiles.profile",
        text=_(
            "%(icon)s Profile",
            icon=LazyString(lambda: f'<i class="{current_theme_icons.user}"></i>'),
        ),
        order=0,
    )
