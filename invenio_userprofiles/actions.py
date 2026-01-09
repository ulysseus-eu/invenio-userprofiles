from time import sleep

from flask import current_app

from invenio_access.permissions import Identity, system_identity
from invenio_search.engine import dsl

from invenio_accounts.proxies import current_datastore
from invenio_communities.fixtures.create_community import create_community
from invenio_communities.members.errors import AlreadyMemberError
from invenio_communities.proxies import current_communities, current_roles
from invenio_communities.utils import slugify_name
from invenio_requests.proxies import current_requests_service
from invenio_userprofiles import UserProfileProxy


def on_profile_created(user_id, uow=None):
    """Execute on user profile created.

    If user has consented and doesn't have its own person community, create it
    """
    # If user has given consent to have a public profile
    # check it has one or create one
    new_community = None
    profile = UserProfileProxy.get_by_userid(int(user_id))
    if profile is not None and profile.consent_by_providing_my_consent:
        # check this user already has a public profile community
        # if yes, reindex it, if not create it
        # import here due to circular import
        user = current_datastore.get_user_by_id(user_id)
        slug = slugify_name(user.username)
        from invenio_communities.members.records.api import Member
        # If user doesn't own a person community
        person_filter = dsl.Q("term", **{"metadata.type.id": "person"})
        community_base_data = {
            "slug": slug,
            "given_name": profile.given_name,
            "family_name": profile.family_name,
            "user_id": str(user_id)
        }
        for deduplication_index in range(10):
            if deduplication_index != 0:
                slug = f"{slugify_name(user.username)}_{deduplication_index}"
                community_base_data["slug"] = slug
            # If the community with the right slug doesn't exist create it
            existing_communities = current_communities.service.search(
                system_identity,
                q=f"slug:{slug}",
                extra_filter=person_filter)
            if existing_communities.total == 0:
                new_community = current_communities.service.create(system_identity, create_community(community_base_data), uow=uow)
                break
            else:
                new_community = next(existing_communities.hits)
                if not Member.has_members(new_community["id"], current_roles.owner_role.name):
                    break

        # If community has been created,
        # invite the user as an owner and accept the invite on his behalf
        if new_community is not None:
            invitation_data = {
                "members": [
                    {
                        "type": "user",
                        "id": str(user_id),
                    }
                ],
                "role": current_roles.owner_role.name,
                "visible": True,
            }
            try:
                existing_invitations = current_communities.service.members.search_invitations(
                    system_identity,
                    new_community["id"],
                    q=f"{user.username}",
                )
                request_id = None
                request_list = []
                if existing_invitations.total == 0:
                    current_app.logger.warning(f"Invitation for community {new_community['id']} not found for user : {user_id}")
                    request_list = current_communities.service.members.invite(
                        system_identity, new_community["id"],
                        invitation_data,
                        uow=uow
                    )
                    current_app.logger.warning(f"Invitation for community {new_community['id']} sent for user : {user_id}")
                    # for i_attempt in range(10):
                    #     current_app.logger.warning(
                    #         f"Attempt {i_attempt} to find invitation for community {new_community['id']} and user : {user_id}")
                    #     existing_invitations = current_communities.service.members.search_invitations(
                    #         system_identity,
                    #         new_community["id"],
                    #         q=f"{user.username}",
                    #         is_open=True
                    #     )
                    #     if existing_invitations.total > 0:
                    #         current_app.logger.warning(
                    #             f"Invitation for community {new_community['id']} found for user : {user_id} at attempt {i_attempt}")
                    #         break
                    #     else:
                    #         sleep(5)
                if existing_invitations.total > 0 or len(request_list) > 0:
                    if existing_invitations.total > 0:
                        invitation_found = next(existing_invitations.hits)
                        request_id = invitation_found["request"]["id"]
                        current_app.logger.warning(f"Invitation for community {new_community['id']} found for user : {user_id}")
                    if len(request_list) > 0:
                        request_id = request_list[0]["id"]
                        current_app.logger.warning(f"Invitation for community {new_community['id']} in request for user : {user_id}")

                    current_requests_service.execute_action(
                        system_identity,
                        request_id,
                        "accept",
                        uow=uow,
                        expand=True
                    )
                    current_app.logger.warning(f"Invitation for community {new_community['id']} accepted for user : {user_id}")
                else:
                    current_app.logger.warning(f"Invitation for community {new_community['id']} still not found for user : {user_id}")

            except AlreadyMemberError:
                pass
            except Exception as e:
                current_app.logger.warning(f"Error while creating community for user : {user_id} : {e}")
                raise e


def on_profile_updated(user_id, uow=None, **kwargs):
    """Execute on user profile updated.

    Re-index user records and dump verified field into records.
    If first name or last name changes, change community metadata
    If user has consented and doesn't have its own person community, create it
    """
    # Check user has given consent
    profile = UserProfileProxy.get_by_userid(int(user_id))
    if profile is not None and profile.consent_by_providing_my_consent:
        # check this user already has a public profile community
        # if yes, reindex it, if not create it
        # import here due to circular import
        user = current_datastore.get_user_by_id(user_id)
        slug = slugify_name(user.username)
        from invenio_communities.members.records.api import Member

        user_owned_communities = [
            m[0] for m in Member.get_memberships(Identity(user_id)) if m[1] == "owner"
        ]
        owned_communities_filter = dsl.Q(
            "terms", **{"id": [id_ for id_ in user_owned_communities]}
        )
        # If user doesn't own a person community
        person_filter = dsl.Q("term", **{"metadata.type.id": "person"})
        missing_user_id_q = dsl.query.Q(
                    "bool", must_not=[dsl.query.Q("exists", field="metadata.person.user_id")]
                )
        empty_user_id_q = dsl.Q('term', **{'metadata.person.user_id': ''})
        missing_or_empty_user_id_q = missing_user_id_q | empty_user_id_q
        has_my_user_id_q = dsl.Q("term", **{"metadata.person.user_id": str(user_id)})
        my_communities_q = (person_filter & missing_or_empty_user_id_q & owned_communities_filter) | (
                    person_filter & has_my_user_id_q)
        my_communities_res = current_communities.service.search(
            system_identity,
            extra_filter=my_communities_q
        )
        community_base_data = {
            "slug": slug,
            "given_name": profile.given_name,
            "family_name": profile.family_name,
            "user_id": str(user_id)
        }
        current_app.logger.warning(f"Entered in on_profile_updated for user : {user_id}")
        if my_communities_res.total == 0:
            current_app.logger.warning(f"There is no community for user : {user_id}")
            on_profile_created(user_id, uow)
        # If the person community for this user exists
        # make sure we update it with last details
        else:
            my_owned_community = next(my_communities_res.hits)
            current_app.logger.warning(f"There is at least one community {my_owned_community['id']} for user : {user_id}")
            current_communities.service.update(
                system_identity,
                my_owned_community["id"],
                create_community(community_base_data),
                uow=uow
            )
            current_app.logger.warning(f"Community {my_owned_community['id']} updated for user : {user_id}")
            # Reindex person community for both profile updates and metadata updates
            # refresh owned communities filter to include any possibly newly created community
            current_communities.service.reindex(system_identity, extra_filter=my_communities_q)
            current_app.logger.warning(f"Community {my_owned_community['id']} reindexed for user : {user_id}")
