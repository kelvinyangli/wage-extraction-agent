# Stage: interpret printed-total relationship

Select only source items that appear to contribute to the supplied printed total. Assign each selected item a multiplier of `1` or `-1`. Do not perform or override arithmetic. Return an empty relationship when the evidence is insufficient.

<payslip_data>
$payslip_context
</payslip_data>

<printed_total>
$printed_total
</printed_total>

Return data conforming exactly to this schema:

$output_schema
