import traceback

from celery import shared_task
from flask import current_app
from invenio_cache.lock import CachedMutex
from invenio_db.uow import UnitOfWork
from invenio_users_resources.services.users.lock import timeout_default
from invenio_users_resources.services.users.tasks import renewal_timeout
from werkzeug.local import LocalProxy


@shared_task(ignore_result=True, acks_late=True, retry=True)
def execute_user_profile_update_actions(user_id=None, action=None):
    """Execute user profile actions.

    Callbacks share the same UOW to guarantee data consistency.
    If any callback fails, then the error is logged and the UOW rolledback.

    Why ``acks_late``:
     - in case the worker fails unexpectedly.
    Why ``retry``:
        - if a task fails, it can be retried afterwards.
    """
    current_actions_registry = LocalProxy(
        lambda: current_app.extensions["invenio-userprofiles"].actions_registry
    )
    """Proxy for the currently instantiated actions registry."""

    class ProfileUpdateMutex(CachedMutex):
        """Wrapper of ``CachedMutex`` to be used solely in user moderation.

        This class forces the lock ID prefix and specifies a default timeout when acquiring the lock.
        """

        lock_id_prefix = "profile_update_lock"

        def __init__(self, user_id):
            """Constructor.

            Creates a lock using the parent constructor, building the lock ID as follows:

                <id_prefix>.<user_id>
            """
            super().__init__(lock_id=f"{self.lock_id_prefix}.{user_id}")

        def acquire(self, timeout=None):
            """Acquires the lock.

            If the timeout is not provided, a default is retrieved from the config USERS_RESOURCES_MODERATION_LOCK_DEFAULT_TIMEOUT
            """
            timeout = timeout or timeout_default
            return super().acquire(timeout=timeout_default)

    actions = current_actions_registry.get(action, [])

    with ProfileUpdateMutex(user_id) as lock:
        lock.acquire_or_renew(renewal_timeout)

        # Create a uow that is shared by all the callables
        uow = UnitOfWork()
        try:
            for callback in actions:
                callback(user_id, uow=uow)
            # Commit the uow when all the callbacks succeeded
            uow.commit()
        except Exception as e:
            tb_str = ''.join(traceback.format_exception(type(e), e, e.__traceback__)) if str(e) == '' else str(e)
            current_app.logger.warning(
                f"Could not execute action '{action}' for user: {tb_str}"
            )
            # If a callback fails, rollback the operation and stop processing callbacks
            uow.rollback()
