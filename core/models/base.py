"""
Base models and mixins.
"""

import json
from typing import Dict, Any, Optional, Type, List, ClassVar
from datetime import date, datetime

from django.db import models
from django.utils import timezone
from django.apps import apps


class TimestampMixin(models.Model):
    """Abstract base model with created and updated timestamps"""

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """Update timestamps on save"""
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)

    def get_formatted_info(self):
        """
        Returns all fields of the model and their values as a formatted string.
        For related data, it returns counts and basic info instead of full details.

        Returns:
            str: Formatted string with all model data
        """
        lines = []
        model_name = self.__class__.__name__
        lines.append(f"{model_name.upper()} INFORMATION")
        lines.append("-" * len(f"{model_name} INFORMATION"))

        # Process all fields on the model
        for field in self.__class__._meta.get_fields():
            field_name = field.name

            # Skip the automatically generated reverse relations unless they're explicitly defined
            if field.is_relation and field.auto_created and not field.concrete:
                # If this is a reverse relation that's defined as a related_name
                if hasattr(field, "related_name") and field.related_name:
                    # Handle many-to-many and one-to-many relationships
                    if field.one_to_many or field.many_to_many:
                        related_objects = getattr(self, field.related_name, None)
                        if related_objects and hasattr(related_objects, "all"):
                            count = related_objects.count()
                            lines.append(f"{field.related_model.__name__} ({count}):")

                            # Show a summary of related objects if there are any
                            if count > 0:
                                for index, obj in enumerate(
                                    related_objects.all()[:5]
                                ):  # Limit to 5
                                    summary = str(obj)
                                    lines.append(f"  - {summary}")
                                if count > 5:
                                    lines.append(f"  ... and {count - 5} more")

            # Regular fields or explicitly defined relations
            elif not field.is_relation or field.concrete:
                value = getattr(self, field_name, None)
                if isinstance(value, models.Model):
                    lines.append(f"{field_name}: {str(value)}")
                else:
                    # Format dates and times nicely
                    if isinstance(value, (datetime, date)):
                        value = (
                            value.strftime("%Y-%m-%d %H:%M:%S")
                            if hasattr(value, "strftime")
                            else str(value)
                        )

                    lines.append(f"{field_name}: {value}")

        return "\n".join(lines)

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """
        Generate a JSON schema for this model.

        Returns:
            A dictionary containing the JSON schema for the model
        """
        # Generate basic schema from model fields
        fields_dict = {}
        required_fields = []

        # Extract information from model fields
        for field in cls._meta.fields:
            field_name = field.name
            field_type = "string"  # Default type

            # Map Django field types to JSON Schema types
            if field.get_internal_type() in (
                "IntegerField",
                "AutoField",
                "BigIntegerField",
                "SmallIntegerField",
            ):
                field_type = "integer"
            elif field.get_internal_type() in ("DecimalField", "FloatField"):
                field_type = "number"
            elif field.get_internal_type() in ("BooleanField", "NullBooleanField"):
                field_type = "boolean"
            elif field.get_internal_type() in ("DateField", "DateTimeField", "TimeField"):
                field_type = "string"
                fields_dict[field_name] = {"type": field_type, "format": "date-time"}
                continue

            fields_dict[field_name] = {"type": field_type}

            # Track required fields
            if not field.null and not field.blank:
                required_fields.append(field_name)

        return {
            "type": "object",
            "title": cls.__name__,
            "properties": fields_dict,
            "required": required_fields,
        }

    @classmethod
    def get_schema_as_json(cls, indent: Optional[int] = 2) -> str:
        """
        Get the JSON schema for this model as a JSON string.

        Args:
            indent: Optional JSON indentation level (default: 2)

        Returns:
            JSON string representation of the schema
        """
        schema = cls.get_schema()
        return json.dumps(schema, indent=indent)

    @staticmethod
    def get_app_schemas(
        app_label: str = "core",
        exclude_models: Optional[List[str]] = None,
        include_abstract: bool = False,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generate JSON schemas for all models in the specified app.

        Args:
            app_label: The Django app label whose models to process
            exclude_models: Optional list of model names to exclude
            include_abstract: Whether to include abstract models (default: False)

        Returns:
            Dictionary mapping model names to their schema definitions
        """
        if exclude_models is None:
            exclude_models = []

        result = {}
        app_models = apps.get_app_config(app_label).get_models()

        for model in app_models:
            model_name = model.__name__
            # Skip abstract models unless explicitly included
            if model_name in exclude_models or (model._meta.abstract and not include_abstract):
                continue

            try:
                # Only generate schema for models that inherit from TimestampMixin
                # and have get_schema method
                if (issubclass(model, TimestampMixin) or include_abstract) and hasattr(
                    model, "get_schema"
                ):
                    # Generate schema using the model's get_schema method
                    schema = model.get_schema()
                    result[model_name] = schema
                else:
                    # For non-TimestampMixin models, generate a basic schema
                    schema = TimestampMixin._generate_basic_schema(model)
                    result[model_name] = schema
            except Exception as e:
                # Log or handle any errors
                print(f"Error generating schema for {model_name}: {str(e)}")

        return result

    @staticmethod
    def _generate_basic_schema(model_class) -> Dict[str, Any]:
        """
        Generate a basic schema for any model class, even if it doesn't inherit from TimestampMixin.

        Args:
            model_class: The Django model class

        Returns:
            A dictionary containing a basic JSON schema for the model
        """
        fields_dict = {}
        required_fields = []

        # Extract information from model fields
        for field in model_class._meta.fields:
            field_name = field.name
            field_type = "string"  # Default type

            # Map Django field types to JSON Schema types
            if field.get_internal_type() in (
                "IntegerField",
                "AutoField",
                "BigIntegerField",
                "SmallIntegerField",
            ):
                field_type = "integer"
            elif field.get_internal_type() in ("DecimalField", "FloatField"):
                field_type = "number"
            elif field.get_internal_type() in ("BooleanField", "NullBooleanField"):
                field_type = "boolean"
            elif field.get_internal_type() in ("DateField", "DateTimeField", "TimeField"):
                field_type = "string"
                fields_dict[field_name] = {"type": field_type, "format": "date-time"}
                continue

            fields_dict[field_name] = {"type": field_type}

            # Track required fields
            if not field.null and not field.blank:
                required_fields.append(field_name)

        return {
            "type": "object",
            "title": model_class.__name__,
            "properties": fields_dict,
            "required": required_fields,
        }

    @staticmethod
    def get_app_schemas_as_json(
        app_label: str = "core",
        exclude_models: Optional[List[str]] = None,
        include_abstract: bool = False,
        indent: Optional[int] = 2,
    ) -> str:
        """
        Generate JSON schemas for all models in the app and return as a JSON string.

        Args:
            app_label: The Django app label whose models to process
            exclude_models: Optional list of model names to exclude
            include_abstract: Whether to include abstract models (default: False)
            indent: Optional JSON indentation level (default: 2)

        Returns:
            JSON string representation of all schemas
        """
        schemas = TimestampMixin.get_app_schemas(
            app_label=app_label, exclude_models=exclude_models, include_abstract=include_abstract
        )
        return json.dumps(schemas, indent=indent)
