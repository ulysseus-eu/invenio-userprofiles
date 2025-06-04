# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2018 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Database models for user profiles."""

from flask import current_app


class AnonymousUserProfile:
    """Anonymous user profile."""

    @property
    def is_anonymous(self):
        """Return whether this UserProfile is anonymous."""
        return True


class UserProfileProxy:
    """Proxy for a user that allows mapping the form to the user object."""

    # profile main tabs
    keys_profile_main_tabs = [
    "Gender",
    "email",
    "University",
    "Others_initiatives",
    "Affiliation_to_entities",
    "family_name",
    "given_name",
    "orcid",
    "linkedin",
    "profile_links",
    "Faculty_Center_Institute",
    "Department",
    "Research_Group_member",
    "Career_stage",
    "Additional_Keywords",
    "Principal_Investigator",
    "Research_Group_PI",
    "Languages",
    "Expert_profile",
    "profile_please_indicate_the_full_name_of_your_research_group_in_english",
    "Areas_of_expertise",
    "Main_Keywords",
    "TRL_level",
    ]
    
    # profile projects tabs
    keys_profile_projects_tabs = [
    "EU_proposal_writer",
    "EU_project_leader",
    "Coordinated_projects_and_calls",
    "EU_project_member",
    "EU_project_evaluator",
    "Knowledge_Transfer",
    "Founder_of_a_spin_off",
    "Member_of_a_spin_off",
    "Patents",
    "Member_of_an_Industrial_Chair",
    "projects_other",
    "projects_other_response",
    "projects_affiliated_relevant_associations_platforms_clusters",
    ]
    
    # profile research_groups tabs
    keys_profile_research_groups_tabs = [
    "Interest_in_Joint_Research_Groups",
    "Relevant_publications",
    "Relevant_projects",
    ]
    
    # profile consent tabs
    keys_profile_consent_tabs = [
    "consent_by_providing_my_consent",
    "Visibility",
    ]

    _profile_attrs = ["full_name", "affiliations"]
    
    _profile_attrs.extend(keys_profile_main_tabs)
    _profile_attrs.extend(keys_profile_projects_tabs)
    _profile_attrs.extend(keys_profile_research_groups_tabs)
    _profile_attrs.extend(keys_profile_consent_tabs)
    
    _preferences_attrs = ["email_visibility", "visibility", "locale", "timezone"]
    _read_only_attrs = ["email_repeat"]
    _aliases = {"email_repeat": "email", "user_id": "id"}

    def __init__(self, user):
        """."""
        super().__setattr__("_user", user)

    def __getattr__(self, attr):
        """."""
        if attr in self._profile_attrs:
            return self._user.user_profile.get(attr, None)
        elif attr in self._preferences_attrs:
            return self._user.preferences.get(attr, None)
        else:
            attr = self._aliases.get(attr, attr)
            return getattr(self._user, attr)

    def __setattr__(self, attr, value):
        """."""
        if attr == "email":
            if (
                current_app.config["USERPROFILES_EMAIL_ENABLED"]
                and self._user.email != value
            ):
                self._user.email = value
                self._user.confirmed_at = None
        elif attr in self._profile_attrs:
            self._user.user_profile = {**self._user.user_profile, attr: value}
        elif attr in self._preferences_attrs:
            self._user.preferences = {**self._user.preferences, attr: value}
        elif attr not in self._read_only_attrs:
            setattr(self._user, attr, value)

    def __hasattr__(self, attr):
        """."""
        if attr in self._profile_attrs:
            return attr in self._user.user_profile
        elif attr in self._preferences_attrs:
            return attr in self._user.preferences[attr]
        else:
            attr = self._aliases.get(attr, attr)
            hasattr(self._user, attr)

    @classmethod
    def get_by_username(cls, username):
        """Get profile by username.

        :param username: A username to query for (case insensitive).
        """
        # Kept for backward compatibility
        user = current_app.extensions["security"].datastore.find_user(
            _username=username.lower()
        )
        return cls(user) if user else None

    @classmethod
    def get_by_userid(cls, user_id):
        """Get profile by user identifier.

        :param user_id: Identifier of a :class:`~invenio_accounts.models.User`.
        :returns: A :class:`~invenio_userprofiles.models.UserProfile` instance
            or ``None``.
        """
        # Kept for backward compatibility
        user = current_app.extensions["security"].datastore.find_user(id=user_id)
        return cls(user) if user else None


# Backward compatibility
UserProfile = UserProfileProxy
