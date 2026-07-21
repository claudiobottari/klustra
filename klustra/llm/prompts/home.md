You are a knowledge architect. Generate the HOME page for this domain — the top-level entry point.

## Domain: {{ domain }}

## Top-level areas ({{ top_nodes | length }} clusters):

{% for n in top_nodes %}
### {{ n.title }}
- **Description:** {{ n.description }}
- **Tags:** {{ n.tags | join(", ") }}
{% endfor %}

## Instructions

1. Produce a TITLE for this domain's home page (e.g., "HV Cable Engineering Knowledge Base").
2. Write a one-sentence DESCRIPTION of what this domain covers.
3. Write BODY_MD (3-5 paragraphs): explain the domain to a new engineer, navigate by areas. Use wikilinks [[entity_id]] to reference the top-level clusters.
4. Produce TAGS (3-6) that characterize the entire domain.
5. Produce ENTITY_ID_SLUG: always use "home" for the home page.
