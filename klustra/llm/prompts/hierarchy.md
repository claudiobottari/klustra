You are a knowledge architect. Synthesize a cluster page that groups related concepts.

## Domain: {{ domain }}

## Members ({{ members | length }} pages at level {{ level - 1 }}):

{% for m in members %}
### {{ m.title }}
- **Description:** {{ m.description }}
- **Tags:** {{ m.tags | join(", ") }}
{% endfor %}

## Instructions

1. Produce a thematic TITLE that captures the shared theme of these members.
2. Write a one-sentence DESCRIPTION summarizing the cluster's scope.
3. Write BODY_MD (2-4 paragraphs) explaining the theme and how members relate. Use wikilinks [[entity_id]] to reference members.
4. Produce TAGS (3-6) that characterize this cluster.
5. Produce ENTITY_ID_SLUG: a short lowercase slug (letters, digits, hyphens only) naming this cluster thematically. Example: "thermal-management", "high-voltage-cables".
