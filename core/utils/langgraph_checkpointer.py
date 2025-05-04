# core/utils/langgraph_checkpointer.py

import logging
from collections import deque
from typing import Any, AsyncIterator, Dict, List, Optional, Sequence, Tuple, Union

from asgiref.sync import sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from core.models.misc import LangGraphCheckpoint

logger = logging.getLogger(__name__)


class DjangoCheckpointSerializer(JsonPlusSerializer):
    """
    Serializer for LangGraph checkpoints using JsonPlusSerializer for broader compatibility.
    Handles special types like deque for proper serialization/deserialization.
    """

    def dumps(self, obj: Any) -> bytes:
        """Serialize object to bytes, handling special types like deque."""
        # Convert deque to list for serialization
        if isinstance(obj, deque):
            obj = list(obj)
        elif isinstance(obj, dict):
            obj = {k: list(v) if isinstance(v, deque) else v for k, v in obj.items()}

        return super().dumps(obj)

    def loads(self, s: Union[bytes, memoryview]) -> Any:
        """
        Deserialize bytes or memoryview to object, handling conversion back to deque.

        Args:
            s: Serialized data as bytes or memoryview from database

        Returns:
            Deserialized Python object
        """
        # Convert memoryview to bytes if needed
        if isinstance(s, memoryview):
            s = bytes(s)

        data = super().loads(s)

        # Convert lists back to deque where needed
        if isinstance(data, dict):
            for field in ["intermediate_steps", "chat_history"]:
                if field in data and isinstance(data[field], list):
                    data[field] = deque(data[field])
        return data


class DjangoCheckpointSaver(BaseCheckpointSaver):
    """
    Stores LangGraph checkpoints in Django using the LangGraphCheckpoint model.

    This implementation provides both synchronous and asynchronous methods
    for checkpoint operations (get, list, put, delete) using Django's ORM.
    """

    serializer = DjangoCheckpointSerializer()

    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """
        Retrieve the latest checkpoint for a thread.

        Args:
            config: RunnableConfig containing thread_id

        Returns:
            CheckpointTuple or None if no checkpoint exists
        """
        thread_id = config["configurable"]["thread_id"]
        try:
            # Get the latest checkpoint for the thread
            checkpoint_model = LangGraphCheckpoint.objects.filter(thread_id=thread_id).first()

            if not checkpoint_model:
                return None

            # Deserialize the checkpoint data
            checkpoint_data = self.serializer.loads(checkpoint_model.checkpoint)

            # Ensure checkpoint has required LangGraph structure
            if isinstance(checkpoint_data, dict):
                # Add required keys if missing
                if "channel_values" not in checkpoint_data:
                    checkpoint_data["channel_values"] = {}

                # Ensure metadata includes 'step' key
                metadata = {"step": 0}
                if "metadata" in checkpoint_data:
                    checkpoint_metadata = checkpoint_data.get("metadata", {})
                    if isinstance(checkpoint_metadata, dict) and "step" in checkpoint_metadata:
                        metadata["step"] = checkpoint_metadata["step"]
            else:
                # If checkpoint_data is not a dict, create a properly structured checkpoint
                checkpoint_data = {"channel_values": {}, "metadata": {"step": 0}}

            # Construct the parent config if parent_ts exists
            parent_config = None
            if checkpoint_model.parent_ts:
                parent_config = {
                    "configurable": {
                        "thread_id": thread_id,
                        "thread_ts": checkpoint_model.parent_ts,
                    }
                }

            # The config for the current checkpoint
            checkpoint_config = {
                "configurable": {
                    "thread_id": thread_id,
                    "thread_ts": checkpoint_model.updated_at.isoformat(),
                }
            }

            return CheckpointTuple(
                config=checkpoint_config,
                checkpoint=checkpoint_data,
                parent_config=parent_config,
                metadata=metadata,
            )
        except ObjectDoesNotExist:
            return None
        except Exception as e:
            logger.exception(f"Error retrieving checkpoint for thread_id {thread_id}: {e}")
            return None

    def list(self, config: RunnableConfig) -> Sequence[CheckpointTuple]:
        """
        List all checkpoints for a thread, ordered by timestamp.

        Args:
            config: RunnableConfig containing thread_id

        Returns:
            Sequence of CheckpointTuple objects
        """
        thread_id = config["configurable"]["thread_id"]
        try:
            # Get all checkpoints for the thread, ordered by timestamp
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

                    # Ensure metadata includes 'step' key
                    metadata = {"step": 0}
                    if isinstance(checkpoint_data, dict) and "metadata" in checkpoint_data:
                        checkpoint_metadata = checkpoint_data.get("metadata", {})
                        if isinstance(checkpoint_metadata, dict) and "step" in checkpoint_metadata:
                            metadata["step"] = checkpoint_metadata["step"]

                    tuples.append(
                        CheckpointTuple(
                            config=checkpoint_config,
                            checkpoint=checkpoint_data,
                            parent_config=parent_config,
                            metadata=metadata,
                        )
                    )
                except Exception as e:
                    logger.error(
                        f"Error deserializing checkpoint during list for thread_id {thread_id}, "
                        f"ts {model.updated_at}: {e}"
                    )
                    continue  # Skip corrupted checkpoints

            return tuples
        except Exception as e:
            logger.exception(f"Error listing checkpoints for thread_id {thread_id}: {e}")
            return []

    @transaction.atomic
    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        """
        Save a new checkpoint for a thread.

        Args:
            config: RunnableConfig containing thread_id
            checkpoint: Checkpoint data to save
            metadata: CheckpointMetadata containing step information
            new_versions: Channel versions

        Returns:
            Updated RunnableConfig with new timestamp
        """
        # Ensure we have metadata with step information
        if not hasattr(metadata, "step"):
            # If metadata doesn't have step attribute, create default
            step = 0
            # Try to get from previous checkpoint if available
            try:
                prev_checkpoint = self.get_tuple(config)
                if prev_checkpoint and prev_checkpoint.metadata:
                    step = prev_checkpoint.metadata.get("step", 0) + 1
            except Exception:
                pass

            # Add step to checkpoint metadata
            if isinstance(checkpoint, dict):
                if "metadata" not in checkpoint:
                    checkpoint["metadata"] = {}
                if isinstance(checkpoint["metadata"], dict):
                    checkpoint["metadata"]["step"] = step
        thread_id = config["configurable"]["thread_id"]
        try:
            if not isinstance(checkpoint, dict):
                error_msg = (
                    f"CRITICAL CHECKPOINT SAVE ERROR for thread {thread_id}: "
                    f"Expected 'checkpoint' argument to be a dict, but received type {type(checkpoint)}. "
                    f"Value Snippet: {str(checkpoint)[:500]}..."
                )
                logger.error(error_msg)
                raise TypeError(error_msg)

            # Serialize the checkpoint data
            serialized_checkpoint = self.serializer.dumps(checkpoint)

            # Get current latest checkpoint to use as parent
            current_latest = LangGraphCheckpoint.objects.filter(thread_id=thread_id).first()
            parent_ts = current_latest.updated_at.isoformat() if current_latest else None

            # Create a new checkpoint entry
            new_checkpoint_model = LangGraphCheckpoint.objects.create(
                thread_id=thread_id, checkpoint=serialized_checkpoint, parent_ts=parent_ts
            )

            # Return config with new timestamp
            saved_config = {
                "configurable": {
                    "thread_id": thread_id,
                    "thread_ts": new_checkpoint_model.updated_at.isoformat(),
                }
            }
            return saved_config
        except Exception as e:
            logger.exception(f"Error saving checkpoint for thread_id {thread_id}: {e}")
            raise

    @transaction.atomic
    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[Tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        """
        Save a batch of writes for a thread.

        Args:
            config: RunnableConfig containing thread_id
            writes: Sequence of (key, value) tuples to write
            task_id: Task ID
            task_path: Task path
        """
        thread_id = config["configurable"]["thread_id"]
        try:
            # First check if a checkpoint exists for this thread
            existing_checkpoint = None
            try:
                existing_tuple = self.get_tuple(config)
                if existing_tuple:
                    existing_checkpoint = existing_tuple.checkpoint
            except Exception:
                pass

            # If we have an existing checkpoint, update it with the writes
            if existing_checkpoint and isinstance(existing_checkpoint, dict):
                checkpoint_data = existing_checkpoint

                # Update with new writes
                for key, value in writes:
                    # If the key is for channel_values, update that dict
                    if key == "channel_values":
                        if "channel_values" not in checkpoint_data:
                            checkpoint_data["channel_values"] = {}
                        checkpoint_data["channel_values"] = value
                    else:
                        # Otherwise update the main checkpoint dict
                        checkpoint_data[key] = value
            else:
                # Create a new properly structured checkpoint
                checkpoint_data = {"channel_values": {}, "metadata": {"step": 0}}

                # Add the writes to the checkpoint
                for key, value in writes:
                    if key == "channel_values":
                        checkpoint_data["channel_values"] = value
                    else:
                        checkpoint_data[key] = value

            # Ensure step is in metadata
            if "metadata" not in checkpoint_data:
                checkpoint_data["metadata"] = {"step": 0}
            elif "step" not in checkpoint_data["metadata"]:
                checkpoint_data["metadata"]["step"] = 0

            # Use put method to save the complete checkpoint
            self.put(
                config,
                checkpoint=checkpoint_data,
                metadata=CheckpointMetadata(task_id=task_id, task_path=task_path),
                new_versions={},
            )
        except Exception as e:
            logger.exception(f"Error during put_writes for thread_id {thread_id}: {e}")
            raise

    @transaction.atomic
    def delete(self, config: RunnableConfig) -> None:
        """
        Delete all checkpoints for a thread.

        Args:
            config: RunnableConfig containing thread_id
        """
        thread_id = config["configurable"]["thread_id"]
        logger.info(f"Deleting checkpoints for thread_id: {thread_id}")
        try:
            deleted_count, _ = LangGraphCheckpoint.objects.filter(thread_id=thread_id).delete()
            logger.info(f"Deleted {deleted_count} checkpoints for thread_id: {thread_id}")
        except Exception as e:
            logger.exception(f"Error deleting checkpoints for thread_id {thread_id}: {e}")
            raise

    # --- Asynchronous API Implementation ---

    @sync_to_async
    def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """Asynchronously get the latest checkpoint tuple for a thread."""
        return self.get_tuple(config)

    async def alist(self, config: RunnableConfig) -> AsyncIterator[CheckpointTuple]:
        """Asynchronously list all checkpoint tuples for a thread."""
        # Get the full list synchronously through sync_to_async
        sync_list = await sync_to_async(self.list)(config)
        # Yield each item to create an async iterator
        for item in sync_list:
            yield item

    @sync_to_async
    def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        """Asynchronously save a checkpoint for a thread."""
        return self.put(config, checkpoint, metadata, new_versions)

    @sync_to_async
    def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[Tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        """Asynchronously save a batch of writes."""
        return self.put_writes(config, writes, task_id, task_path)

    @sync_to_async
    def adelete(self, config: RunnableConfig) -> None:
        """Asynchronously delete all checkpoints for a thread."""
        return self.delete(config)
