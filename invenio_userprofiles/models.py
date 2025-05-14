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
    "profile_genre",
    "profile_university",
    "profile_links",
    "profile_faculty",
    "profile_department",
    "profile_research_group",
    "profile_career_stage",
    "profile_keywords",
    "profile_if_not_please_state_the_full_name_of_the_principal_investigator_of_your_research_group_please_use_this_format_first_name_last_name",
    "profile_if_not_please_state_the_full_name_of_the_principal_investigator_of_your_research_group_please_use_this_format_first_name_last_name_write_name",
    "profile_languages",
    "profile_identify",
    "profile_please_indicate_the_full_name_of_your_research_group_in_english",
    "profile_expertise_1",
    "profile_expertise_2",
    "profile_research_area",
    ]
    
    # profile projects tabs
    keys_profile_projects_tabs = [
    "projects_have_you_ever_designed_or_written_a_european_project_proposal",
    "projects_have_you_ever_participated_in_a_granted_european_project_as_consortium_leader",
    "projects_if_yes_please_name_the_project_s_you_have_coordinated_including_the_corresponding_call_s",
    "projects_have_you_ever_participated_in_a_granted_european_project_as_a_member_of_consortium",
    "projects_have_you_been_an_evaluator_of_eu_projects",
    "projects_has_your_research_resulted_in_a_knowledge_transfer_initiative",
    "projects_i_have_founded_a_spin_off_company_as_a_result_of_my_research",
    "projects_i_am_a_member_of_a_spin_off_company_linked_to_my_university",
    "projects_are_you_the_principal_investigator_of_your_research_group",
    "projects_i_have_patented_the_results_of_my_research",
    "projects_i_am_an_active_member_of_a_business_chair_linked_to_my_university",
    "projects_other",
    "projects_other_response",
    "projects_affiliated_relevant_associations_platforms_clusters",
    ]
    
    # profile research_groups tabs
    keys_profile_research_groups_tabs = [
    "research_group_are_you_interested_in_participating_in_building_joint_research_groups_centered_around_shared_research_disciplines_within_ulysseus_partner_universities",
    "research_group_most_relevant_to_your_research",
    "research_group_information_on_the_most_significant_projects",
    ]
    
    # profile consent tabs
    keys_profile_consent_tabs = [
    "consent_by_providing_my_consent",
    "consent_profile_privacy_level",
    ]

    _profile_attrs = ["full_name", "affiliations"]
    
    _profile_attrs.extend(keys_profile_main_tabs)
    _profile_attrs.extend(keys_profile_projects_tabs)
    _profile_attrs.extend(keys_profile_research_groups_tabs)
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
