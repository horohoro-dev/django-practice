"""Django models.pyからMermaid ER図を生成するコマンド"""

from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import models


class Command(BaseCommand):
    help = "Generate Mermaid ER diagram from Django models"
    FIELD_TYPE_MAPPING = {
        "AutoField": "int",
        "BigAutoField": "bigint",
        "IntegerField": "int",
        "PositiveIntegerField": "int",
        "PositiveSmallIntegerField": "smallint",
        "SmallIntegerField": "smallint",
        "CharField": "string",
        "TextField": "text",
        "EmailField": "string",
        "URLField": "string",
        "SlugField": "string",
        "UUIDField": "uuid",
        "DecimalField": "decimal",
        "FloatField": "float",
        "BinaryField": "binary",
        "BooleanField": "boolean",
        "NullBooleanField": "boolean",
        "JSONField": "json",
        "DateField": "date",
        "DateTimeField": "datetime",
        "DurationField": "duration",
        "TimeField": "time",
        "FileField": "file",
        "ImageField": "image",
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            "-o",
            type=str,
            default="docs/er-diagram.md",
            help="Output file path (default: docs/er-diagram.md)",
        )
        parser.add_argument(
            "--app",
            "-a",
            type=str,
            default="data",
            help="App label to generate ER diagram for (default: data)",
        )

    def _normalize_type(self, field):
        internal_type = field.get_internal_type()
        if isinstance(field, models.DecimalField):
            return f"decimal({field.max_digits},{field.decimal_places})"
        return self.FIELD_TYPE_MAPPING.get(internal_type, internal_type.lower())

    def _get_field_type(self, field):
        """フィールドの型名を取得"""
        if isinstance(field, models.ManyToManyField):
            return "relation", "M2M"
        if isinstance(field, models.OneToOneField):
            field_type = self._normalize_type(field.target_field)
            key_type = "PK" if field.primary_key else "FK"
            return field_type, key_type
        if isinstance(field, models.ForeignKey):
            field_type = self._normalize_type(field.target_field)
            return field_type, "FK"
        if hasattr(field, "get_internal_type"):
            field_type = self._normalize_type(field)
            key_type = "PK" if getattr(field, "primary_key", False) else ""
            return field_type, key_type
        return None, ""

    def _format_option_value(self, value):
        if callable(value):
            return getattr(value, "__qualname__", getattr(value, "__name__", repr(value)))
        return repr(value)

    def _format_field_options(self, field):
        try:
            _, _, _, field_kwargs = field.deconstruct()
        except Exception:  # pragma: no cover - should rarely happen
            field_kwargs = {}

        options = []
        for key, value in field_kwargs.items():
            if key in {"help_text", "verbose_name"}:
                continue
            options.append(f"{key}={self._format_option_value(value)}")
        return ", ".join(options)

    def handle(self, *args, **options):
        output_path = Path(options["output"])
        app_label = options["app"]
        app_models = list(apps.get_app_config(app_label).get_models())

        mermaid_lines = ["erDiagram"]
        relationships = []
        table_definitions = []

        for model in app_models:
            model_name = model.__name__
            model_doc = model.__doc__ or ""
            fields_lines = []
            table_rows = []

            for field in model._meta.get_fields():
                if getattr(field, "auto_created", False) and not isinstance(
                    field, models.ManyToManyField
                ):
                    continue

                field_type, key_type = self._get_field_type(field)
                if field_type is None:
                    continue

                # フィールド名（実際の列名を利用）
                if isinstance(field, models.ManyToManyField):
                    field_name = field.name
                else:
                    field_name = getattr(field, "attname", field.name)

                # リレーションの追加
                if isinstance(field, models.ForeignKey):
                    related_model = field.related_model.__name__
                    relationships.append(
                        f'    {model_name} }}o--|| {related_model} : "{field.name}"'
                    )
                elif isinstance(field, models.OneToOneField):
                    related_model = field.related_model.__name__
                    relationships.append(
                        f'    {model_name} ||--|| {related_model} : "{field.name}"'
                    )
                elif isinstance(field, models.ManyToManyField):
                    related_model = field.related_model.__name__
                    relationships.append(
                        f'    {model_name} }}o--o{{ {related_model} : "{field.name}"'
                    )

                # テーブル定義用の行（help_text取得）
                help_text = getattr(field, "help_text", "") or ""
                if isinstance(field, models.ManyToManyField):
                    relation_info = f"Relates to {field.related_model.__name__}"
                    help_text = f"{help_text} {relation_info}".strip()
                sanitized_help = " ".join(help_text.split()).replace('"', "'")
                help_literal = f'"{sanitized_help}"' if sanitized_help else '""'

                # Mermaid用の行（型,列名,キー種別,help_textの順）
                field_parts = [field_type, field_name]
                if key_type:
                    field_parts.append(key_type)
                field_parts.append(help_literal)
                fields_lines.append("        " + " ".join(field_parts))

                options = self._format_field_options(field)
                options_str = options or "-"
                table_rows.append(
                    f"| {field_name} | {field_type} | {key_type} | {help_text} | {options_str} |"
                )

            if fields_lines:
                mermaid_lines.append(f"    {model_name} {{")
                mermaid_lines.extend(fields_lines)
                mermaid_lines.append("    }")

            # テーブル定義セクション
            if table_rows:
                table_def = f"### {model_name}\n\n{model_doc}\n\n"
                table_def += "| Column | Type | Key | Description | Options |\n"
                table_def += "|--------|------|-----|-------------|---------|\n"
                table_def += "\n".join(table_rows)
                table_definitions.append(table_def)

        mermaid_lines.extend(list(dict.fromkeys(relationships)))

        markdown_content = f"""# ER Diagram

```mermaid
{chr(10).join(mermaid_lines)}
```

---

## Table Definitions

{chr(10).join(table_definitions)}
"""

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown_content)

        self.stdout.write(self.style.SUCCESS(f"ER diagram generated: {output_path}"))
