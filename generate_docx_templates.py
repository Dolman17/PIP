import os
from docx import Document

# Base folder inside your project
BASE = os.path.join(os.path.dirname(__file__), 'templates', 'docx')
os.makedirs(BASE, exist_ok=True)

# 1) Invite Letter
doc = Document()
doc.add_heading('Invite to Performance Improvement Plan Meeting', level=1)
doc.add_paragraph('Date: {{ pip.start_date.strftime("%d %b %Y") }}')
doc.add_paragraph('To: {{ employee.first_name }} {{ employee.last_name }}')
doc.add_paragraph('')
doc.add_paragraph('Dear {{ employee.first_name }},')
doc.add_paragraph(
    'We invite you to a meeting on ' +
    '{{ pip.review_date.strftime("%d %b %Y") }} to discuss your Performance Improvement Plan.'
)
doc.add_paragraph('')
doc.add_paragraph('Sincerely,')
doc.add_paragraph('{{ pip.created_by or current_user.username }}')
doc.save(os.path.join(BASE, 'invite_letter_template.docx'))

# 2) Plan Template
doc = Document()
doc.add_heading('Performance Improvement Plan', level=1)
doc.add_paragraph('Employee: {{ employee.first_name }} {{ employee.last_name }}')
doc.add_paragraph('Start Date: {{ pip.start_date.strftime("%d %b %Y") }}')
doc.add_paragraph('Review Date: {{ pip.review_date.strftime("%d %b %Y") }}')
doc.add_paragraph('')
doc.add_paragraph('Concerns:')
doc.add_paragraph('{{ pip.concerns }}')
doc.add_paragraph('')
doc.add_paragraph('Action Plan:')
doc.add_paragraph('{% for action in pip.action_items %}- {{ action.description }} [{{ action.status }}]{% endfor %}')
doc.save(os.path.join(BASE, 'plan_template.docx'))

# 3) Outcome Letter
doc = Document()
doc.add_heading('Outcome of Performance Improvement Plan', level=1)
doc.add_paragraph('Date: {{ pip.last_updated.strftime("%d %b %Y") }}')
doc.add_paragraph('Employee: {{ employee.first_name }} {{ employee.last_name }}')
doc.add_paragraph('')
doc.add_paragraph('Dear {{ employee.first_name }},')
doc.add_paragraph('The outcome of your Performance Improvement Plan is: {{ pip.status }}.')
doc.add_paragraph('')
doc.add_paragraph('Sincerely,')
doc.add_paragraph('{{ pip.created_by or current_user.username }}')
doc.save(os.path.join(BASE, 'outcome_letter_template.docx'))

print("Templates written to:", BASE)
