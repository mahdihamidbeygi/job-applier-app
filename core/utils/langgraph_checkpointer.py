# core/utils/langgraph_checkpointer.py

import logging
from typing import Any, AsyncIterator, Dict, List, Optional, Sequence, Union

from asgiref.sync import sync_to_async  # Import sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction  # Import transaction for atomic operations
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver, CheckpointTuple
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from core.models.misc import LangGraphCheckpoint  # Import your Django model

logger = logging.getLogger(__name__)


class DjangoCheckpointSerializer(JsonPlusSerializer):
    """
    Use LangGraph's recommended JsonPlusSerializer for broader compatibility
    than pickle, storing the result as bytes in the BinaryField.
    """

    def dumps(self, obj: Any) -> bytes:
        # Call the parent serializer
        serialized_data: bytes = super().dumps(obj)

        # Ensure the parent returned bytes as observed in logs
        if not isinstance(serialized_data, bytes):
            # If it ever returns str again, handle it or raise error
            if isinstance(serialized_data, str):
                logger.warning("JsonPlusSerializer.dumps() returned str, encoding to bytes.")
                return serialized_data.encode("utf-8")
            else:
                raise TypeError(
                    f"Unexpected serialization result type from super().dumps: {type(serialized_data)}"
                )

        # Return the bytes directly (as observed in the warning)
        return serialized_data

    def loads(self, s: Union[bytes, memoryview]) -> Any:  # <-- Accept Union type hint
        """
        Loads data from bytes or memoryview retrieved from the database.
        Converts memoryview to bytes before decoding.
        """
        # Allow bytes or memoryview from the database BinaryField
        if isinstance(s, memoryview):
            # Convert memoryview to bytes before decoding
            s_bytes: bytes = s.tobytes()
        elif isinstance(s, bytes):
            s_bytes: bytes = s
        else:
            # Keep the original check for truly unexpected types
            raise TypeError(f"Expected bytes or memoryview for loads, got {type(s)}")

        # Decode the bytes to string for JsonPlusSerializer.loads
        try:
            decoded_s: str = s_bytes.decode("utf-8")
        except UnicodeDecodeError as e:
            logger.error(f"Failed to decode checkpoint data as UTF-8: {e}")
            # Handle error appropriately, maybe return None or raise a custom exception
            # For now, re-raising might be best to surface the issue
            raise ValueError("Checkpoint data is not valid UTF-8") from e

        return super().loads(decoded_s)


class DjangoCheckpointSaver(BaseCheckpointSaver):
    """
    Stores LangGraph checkpoints in the Django database using the LangGraphCheckpoint model.
    Uses LangGraph's JsonPlusSerializer for serialization.
    Includes both synchronous and asynchronous methods.
    """

    serializer = DjangoCheckpointSerializer()

    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        thread_id = config["configurable"]["thread_id"]
        try:
            # Get the latest checkpoint for the thread based on Django model's ordering
            checkpoint_model = LangGraphCheckpoint.objects.filter(
                thread_id=thread_id
            ).first()  # .first() uses Meta ordering
            if not checkpoint_model:
                logger.debug(f"No checkpoint found for thread_id: {thread_id}")
                return None

            # Deserialize the checkpoint data using the custom serializer
            checkpoint_data = self.serializer.loads(checkpoint_model.checkpoint)

            # Construct the parent config if parent_ts exists
            parent_config = None
            if checkpoint_model.parent_ts:
                parent_config = {
                    "configurable": {
                        "thread_id": thread_id,
                        "thread_ts": checkpoint_model.parent_ts,
                    }
                }

            # The config for the *current* checkpoint uses its own timestamp
            checkpoint_config = {
                "configurable": {
                    "thread_id": thread_id,
                    "thread_ts": checkpoint_model.updated_at.isoformat(),  # Use updated_at as the timestamp
                }
            }

            return CheckpointTuple(
                config=checkpoint_config,
                checkpoint=checkpoint_data,
                parent_config=parent_config,
            )
        except ObjectDoesNotExist:  # Should be caught by .first() returning None, but good practice
            logger.debug(f"No checkpoint found for thread_id: {thread_id}")
            return None
        except Exception as e:
            logger.exception(f"Error retrieving checkpoint tuple for thread_id {thread_id}: {e}")
            return None  # Return None on error

    def list(self, config: RunnableConfig) -> Sequence[CheckpointTuple]:
        thread_id = config["configurable"]["thread_id"]
        try:
            # Get all checkpoints for the thread, oldest first for history
            checkpoint_models = LangGraphCheckpoint.objects.filter(thread_id=thread_id).order_by(
                "updated_at"
            )
            tuples = []
            for model in checkpoint_models:
                try:
                    checkpoint_data = self.serializer.loads(model.checkpoint)
                    # Construct parent config if parent_ts exists
                    parent_config = None
                    if model.parent_ts:
                        parent_config = {
                            "configurable": {
                                "thread_id": thread_id,
                                "thread_ts": model.parent_ts,
                            }
                        }
                    # Config for this specific checkpoint
                    checkpoint_config = {
                        "configurable": {
                            "thread_id": thread_id,
                            "thread_ts": model.updated_at.isoformat(),
                        }
                    }
                    tuples.append(
                        CheckpointTuple(
                            config=checkpoint_config,
                            checkpoint=checkpoint_data,
                            parent_config=parent_config,
                        )
                    )
                except Exception as e:  # Catch deserialization errors per checkpoint
                    logger.error(
                        f"Error deserializing checkpoint during list for thread_id {thread_id}, ts {model.updated_at}: {e}"
                    )
                    continue  # Skip corrupted checkpoints
            return tuples
        except Exception as e:
            logger.exception(f"Error listing checkpoints for thread_id {thread_id}: {e}")
            return []  # Return empty list on error

    @transaction.atomic  # Ensure atomic save operation
    def put(
        self, config: RunnableConfig, checkpoint: Dict[str, Any], *args, **kwargs
    ) -> RunnableConfig:
        thread_id = config["configurable"]["thread_id"]
        try:
            # Serialize the checkpoint data
            serialized_checkpoint = self.serializer.dumps(checkpoint)

            # Determine parent_ts (LangGraph might put it in the checkpoint dict or manage it via config)
            # Let's assume for now we retrieve the *current* latest ts to use as parent_ts for the *new* one
            current_latest = LangGraphCheckpoint.objects.filter(
                thread_id=thread_id
            ).first()  # Get latest based on Meta ordering
            parent_ts = current_latest.updated_at.isoformat() if current_latest else None

            # Create a new checkpoint entry
            # The 'ts' of the new checkpoint will be its 'updated_at' field upon saving
            new_checkpoint_model = LangGraphCheckpoint.objects.create(
                thread_id=thread_id, checkpoint=serialized_checkpoint, parent_ts=parent_ts
            )
            logger.debug(
                f"Saved checkpoint for thread_id: {thread_id} with ts: {new_checkpoint_model.updated_at.isoformat()}"
            )

            # Return a config that includes the timestamp of the checkpoint just saved
            saved_config = {
                "configurable": {
                    "thread_id": thread_id,
                    "thread_ts": new_checkpoint_model.updated_at.isoformat(),
                }
            }
            return saved_config
        except Exception as e:
            logger.exception(f"Error saving checkpoint for thread_id {thread_id}: {e}")
            raise  # Re-raise errors after logging

    @transaction.atomic  # Ensure atomic save operation for the whole batch
    def put_writes(
        self, config: RunnableConfig, checkpoints: List[Dict[str, Any]], *args, **kwargs
    ) -> None:
        """
        Save a batch of checkpoints.
        Note: The base implementation raises NotImplementedError.
        """
        thread_id = config["configurable"]["thread_id"]
        logger.debug(
            f"Executing put_writes for thread {thread_id} with {len(checkpoints)} checkpoints."
        )
        try:
            # Get the timestamp of the latest existing checkpoint *before* this batch starts
            current_latest = LangGraphCheckpoint.objects.filter(thread_id=thread_id).first()
            last_ts = current_latest.updated_at.isoformat() if current_latest else None

            for checkpoint_data in checkpoints:
                serialized_checkpoint = self.serializer.dumps(checkpoint_data)
                # Use the timestamp of the *previous* checkpoint in the batch
                # (or the initial latest) as the parent_ts for the current one.
                parent_ts = last_ts
                new_checkpoint_model = LangGraphCheckpoint.objects.create(
                    thread_id=thread_id, checkpoint=serialized_checkpoint, parent_ts=parent_ts
                )
                # Update last_ts to the timestamp of the checkpoint just saved,
                # so it becomes the parent for the *next* one in the batch.
                last_ts = new_checkpoint_model.updated_at.isoformat()
                logger.debug(f"Saved checkpoint (batch) for thread {thread_id} with ts: {last_ts}")

            # put_writes typically doesn't return anything, unlike put
            return

        except Exception as e:
            logger.exception(f"Error during put_writes for thread_id {thread_id}: {e}")
            raise  # Re-raise errors

    # --- Helper Sync Methods for Async Wrappers ---
    # These simply contain the logic of the original sync methods

    def _get_tuple_sync(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        return self.get_tuple(config)  # Call the original sync method

    def _list_sync(self, config: RunnableConfig) -> Sequence[CheckpointTuple]:
        return self.list(config)  # Call the original sync method

    def _put_sync(
        self, config: RunnableConfig, checkpoint: Dict[str, Any], *args, **kwargs
    ) -> RunnableConfig:
        # Need to re-wrap in transaction.atomic for the sync_to_async call if needed,
        # or ensure the original put method handles it. Since original `put` has it, we just call it.
        return self.put(config, checkpoint, *args, **kwargs)  # Call the original sync method

    def _put_writes_sync(
        self, config: RunnableConfig, checkpoints: List[Dict[str, Any]], *args, **kwargs
    ) -> None:
        # Call the synchronous put_writes. It already handles the transaction.
        self.put_writes(config, checkpoints, *args, **kwargs)

    # --- Asynchronous Methods ---

    @sync_to_async
    def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """Asynchronously get the latest checkpoint tuple for a thread."""
        # sync_to_async wraps the call to the synchronous ORM logic
        return self._get_tuple_sync(config)

    async def alist(self, config: RunnableConfig) -> AsyncIterator[CheckpointTuple]:
        """Asynchronously list all checkpoint tuples for a thread."""
        # Get the full list synchronously first
        sync_list = await sync_to_async(self._list_sync)(config)
        # Yield each item to create an async iterator
        for item in sync_list:
            yield item

    @sync_to_async
    def aput(
        self, config: RunnableConfig, checkpoint: Dict[str, Any], *args, **kwargs
    ) -> RunnableConfig:
        """Asynchronously save a checkpoint for a thread."""
        # sync_to_async wraps the call to the synchronous ORM logic
        return self._put_sync(config, checkpoint, *args, **kwargs)

    @sync_to_async
    def aput_writes(
        self, config: RunnableConfig, checkpoints: List[Dict[str, Any]], *args, **kwargs
    ) -> None:
        """Asynchronously save a batch of checkpoints."""
        return self._put_writes_sync(config, checkpoints, *args, **kwargs)
