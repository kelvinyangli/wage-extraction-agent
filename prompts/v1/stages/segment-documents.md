# Stage: segment documents

Identify payslip boundaries, supported continuations and unresolved sections.

Continue a preceding payslip when later pages contain compatible identity and pay-period evidence and no clear separator. Start a new payslip when strong employer, employee, pay-period, identifier or heading evidence establishes a boundary. Use `uncertain` rather than guessing when evidence conflicts or remains insufficient. Assign every page exactly once.

<document_data>
$document_context
</document_data>

Return data conforming exactly to this schema:

$output_schema
