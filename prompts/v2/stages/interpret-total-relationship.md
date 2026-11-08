# Stage: interpret printed-total relationship

Interpret the supplied printed total in the context and select the source records that appear to contribute to it. A source record may be a pay item or another printed total when the payslip structure supports that relationship. Do not use a predetermined item list, reference the target total itself, or combine a subtotal with its constituent rows. Assign each selected source record a multiplier of `1` or `-1`. Do not perform or override arithmetic. Return an empty relationship when the evidence is insufficient.

<payslip_data>
$payslip_context
</payslip_data>

<printed_total>
$printed_total
</printed_total>

Return data conforming exactly to this schema:

$output_schema
