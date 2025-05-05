"""
Export schema management command.
"""

import os
import json
from typing import Dict, Any, Optional
from django.core.management.base import BaseCommand, CommandError
from django.apps import apps

from core.models.base import TimestampMixin


class Command(BaseCommand):
    help = "Export JSON schema for Django models"

    def add_arguments(self, parser):
        parser.add_argument(
            "--model",
            type=str,
            help="Model name to export schema for",
        )
        parser.add_argument(
            "--app",
            type=str,
            help="App name to export all model schemas for",
            default="core",
        )
        parser.add_argument(
            "--output",
            type=str,
            help="Output file path (default: schema_output.json)",
            default="schema_output.json",
        )
        parser.add_argument(
            "--include-abstract",
            action="store_true",
            help="Include abstract models in the schema",
            default=False,
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Export schemas for all apps and models",
            default=False,
        )

    def handle(self, *args, **options):
        output_file = options["output"]
        model_name = options.get("model")
        app_name = options.get("app", "core")  # Default to 'core' if not provided
        include_abstract = bool(options.get("include_abstract", False))
        export_all = bool(options.get("all", False))

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)

        try:
            # Export schema for a specific model
            if model_name:
                self.stdout.write(f"Exporting schema for model: {model_name}")

                # Find the model in any app
                found = False
                for app_config in apps.get_app_configs():
                    try:
                        model = apps.get_model(app_config.label, model_name)
                        schema = TimestampMixin._generate_basic_schema(model)

                        with open(output_file, "w") as f:
                            json.dump(schema, f, indent=2)

                        found = True
                        self.stdout.write(
                            self.style.SUCCESS(f"Schema for {model_name} exported to {output_file}")
                        )
                        break
                    except LookupError:
                        continue

                if not found:
                    raise CommandError(f"Model '{model_name}' not found")

            # Export schemas for all models in an app
            elif not export_all:
                self.stdout.write(f"Exporting schemas for all models in app: {app_name}")

                try:
                    schemas = TimestampMixin.get_app_schemas(
                        app_label=str(app_name), include_abstract=include_abstract
                    )

                    with open(output_file, "w") as f:
                        json.dump(schemas, f, indent=2)

                    self.stdout.write(
                        self.style.SUCCESS(f"Schemas for app {app_name} exported to {output_file}")
                    )
                except LookupError:
                    raise CommandError(f"App '{app_name}' not found")

            # Export schemas for all apps and models
            else:
                self.stdout.write("Exporting schemas for all apps and models")

                result = {}
                for app_config in apps.get_app_configs():
                    app_label = app_config.label
                    # Skip Django's built-in apps
                    if app_label.startswith("django."):
                        continue

                    try:
                        app_schemas = TimestampMixin.get_app_schemas(
                            app_label=app_label, include_abstract=include_abstract
                        )

                        if app_schemas:  # Only include apps with models
                            result[app_label] = app_schemas
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Error getting schemas for app {app_label}: {str(e)}"
                            )
                        )
                        continue

                with open(output_file, "w") as f:
                    json.dump(result, f, indent=2)

                self.stdout.write(
                    self.style.SUCCESS(f"Schemas for all apps exported to {output_file}")
                )

        except Exception as e:
            raise CommandError(f"Error exporting schema: {str(e)}")
