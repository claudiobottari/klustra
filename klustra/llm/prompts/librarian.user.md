## Entity: {{ entity_id }}
{% if existing_index %}
## Valid wikilink targets
{{ existing_index | join(", ") }}
{% endif %}
{%- for contrib in contributions %}
## Source: {{ contrib.source_id }} ({{ contrib.source_path }})
{%- for unit in contrib.units %}
### [{{ unit.kind }}] {{ unit.locator }}
{{ unit.content_md }}
{% endfor -%}
{%- endfor %}