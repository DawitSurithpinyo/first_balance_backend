from pymongo import MongoClient, ReturnDocument
from redis import Redis


class userRepository:
    def __init__(self, mongo: MongoClient, redisSession: Redis):
        self.mongoClient = mongo
        self.sessionRedis = redisSession

    def patchUserCredentials(
            self, 
            user: dict, 
            filter: dict,
            projection: dict | None = None
        ) -> dict:
        """
            PATCH/upsert user credentials document. Supply `filter` for finding which document to PATCH.
            .. Return the upserted document. Use the `projection` argument to specify which fields to include or exclude in the return document.
            .. note:: INCOMING FIELDS IN `user` and `filter` MUST BE DEFINED WITHIN `normalUserWithPassword` or `googleUser` TYPE.

            :param user: `dict` of classes :class:`~src.types.user.common.normalUserWithPassword`, `googleUser` or a subset of them. Equivalent to `Partial<normalUserWithPassword>` or `Partial<googleUser>` if it was Typescript.
            :param filter: use directly in `collection.find_one_and_update()` to find wanted document. Must be `dict` of classes :class:`~src.types.user.common.normalUserWithPassword`, `googleUser` or a subset of them.
            :param projection:
                - Optional. A dict to specify what fields to include or exclude in the return document. Return all fields if not specified.
                Will be passed directly to the `projection` argument of `collection.find_one_and_update()`.

                - NOTE: SHOULD supply fields belonging to `src.types.user.common.normalUserWithPassword`, `googleUser` types.
        """
        db = self.mongoClient['userCredsDB']
        col = db['credsCollection']

        result = col.find_one_and_update(
            filter = filter,
            update = {
                '$set': user
            },
            upsert = True,
            return_document = ReturnDocument.AFTER,
            projection = projection
        )
        
        return result
    
    def getUserCredentials(self, filter: dict, projection: dict | None = None) -> dict | None:
        """
            Get credentials of a user from database by `filter`.
            .. Return the document. If none is found, return `None`. Use the `projection` argument to specify which fields to include or exclude in the return document.

            :param filter: A dict to specify which document to look for. Will be passed directly to `filter` argument of `collection.find_one()`.
            :param projection: 
                - Optional. A dict to specify what fields to include or exclude in the return document. Return all fields if not specified.
                Will be passed directly to the `projection` argument of `collection.find_one()`.

                - NOTE: SHOULD supply fields belonging to `src.types.user.common.normalUserWithPassword`, `googleUser` types.
        """
        db = self.mongoClient['userCredsDB']
        col = db['credsCollection']

        result = col.find_one(
            filter = filter,
            projection = projection
        )
        
        return result
    
    def deleteUserCredentials(self, filter: dict, fieldsToDelete: list[str] | None = None, projection: dict | None = None) -> dict | None:
        """
            Delete some fields or the entire credential document that matches the `filter`.
            .. Return the deleted document. Use the `projection` argument to specify which fields to include or exclude in the return document.

            :param fieldsToDelete: Optional. List of fields to delete in the document. *If not specified, the* ***entire credentials document*** *will be deleted.*

                - NOTE: SHOULD supply fields belonging to `src.types.user.common.normalUserWithPassword`, `googleUser` types.

            :param filter: A dict to specify which document to delete. Will be passed directly to the `filter` argument of `collection.find_one_and_delete()` or `collection.find_one_and_update()`.
            :param projection: 
                - Optional. A dict to specify what fields to include or exclude in the return document. Return all fields if not specified.
                Will be passed directly to the `projection` argument of `collection.find_one_and_delete()` or `collection.find_one_and_update()`.

                - NOTE: SHOULD supply fields belonging to `src.types.user.common.normalUserWithPassword`, `googleUser` types.
        """
        db = self.mongoClient['userCredsDB']
        col = db['credsCollection']

        if fieldsToDelete is None:
            # If fieldsToDelete is not specified, delete the whole document
            result = col.find_one_and_delete(
                filter = filter,
                projection = projection
            )
        else:
            toDelete: dict = {}
            for field in fieldsToDelete:
                toDelete[field] = ""

            result = col.find_one_and_update(
                filter = filter,
                update = {
                    '$unset': toDelete
                },
                projection = projection
            )

        return result