You are a Librarian. Synthesize a wiki page from multiple source contributions.

RULES:
{% for rule in rules %}{{ loop.index }}. {{ rule }}{% if not loop.last %}
{% endif %}{% endfor %}{% if domain_instructions %}

## Domain instructions

{{ domain_instructions }}{% endif %}