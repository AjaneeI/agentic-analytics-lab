import unittest

from src.routing.validation import (
    ValidationContext,
    ValidationDisposition,
    ValidationReason,
    validate_execution,
)


class TestControlPlaneValidation(unittest.TestCase):
    def test_valid_output_with_evidence_is_accepted(self):
        result = validate_execution(
            ValidationContext(output_valid=True, evidence_satisfied=True)
        )

        self.assertEqual(result.disposition, ValidationDisposition.ACCEPT)
        self.assertEqual(result.reason, ValidationReason.VALIDATED)

    def test_valid_output_without_required_evidence_is_accepted(self):
        result = validate_execution(
            ValidationContext(
                output_valid=True,
                evidence_satisfied=False,
                evidence_required=False,
            )
        )

        self.assertEqual(result.disposition, ValidationDisposition.ACCEPT)
        self.assertEqual(result.reason, ValidationReason.VALIDATED)

    def test_security_boundary_violation_fails_closed_even_if_output_is_valid(self):
        result = validate_execution(
            ValidationContext(
                output_valid=True,
                evidence_satisfied=True,
                security_boundary_violated=True,
            )
        )

        self.assertEqual(result.disposition, ValidationDisposition.FAIL_CLOSED)
        self.assertEqual(
            result.reason,
            ValidationReason.SECURITY_BOUNDARY_VIOLATION,
        )

    def test_retryable_failure_retries_with_budget_remaining(self):
        result = validate_execution(
            ValidationContext(
                output_valid=False,
                evidence_satisfied=False,
                retryable_failure=True,
                retry_count=0,
                max_retries=1,
            )
        )

        self.assertEqual(result.disposition, ValidationDisposition.RETRY)
        self.assertEqual(result.reason, ValidationReason.RETRYABLE_FAILURE)

    def test_retryable_failure_escalates_after_retry_budget_is_exhausted(self):
        result = validate_execution(
            ValidationContext(
                output_valid=False,
                evidence_satisfied=False,
                retryable_failure=True,
                retry_count=1,
                max_retries=1,
            )
        )

        self.assertEqual(result.disposition, ValidationDisposition.ESCALATE)
        self.assertEqual(result.reason, ValidationReason.OUTPUT_INVALID)

    def test_invalid_output_escalates(self):
        result = validate_execution(
            ValidationContext(output_valid=False, evidence_satisfied=True)
        )

        self.assertEqual(result.disposition, ValidationDisposition.ESCALATE)
        self.assertEqual(result.reason, ValidationReason.OUTPUT_INVALID)

    def test_missing_required_evidence_escalates(self):
        result = validate_execution(
            ValidationContext(
                output_valid=True,
                evidence_satisfied=False,
                evidence_required=True,
            )
        )

        self.assertEqual(result.disposition, ValidationDisposition.ESCALATE)
        self.assertEqual(result.reason, ValidationReason.EVIDENCE_MISSING)

    def test_negative_retry_count_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "retry_count"):
            ValidationContext(
                output_valid=False,
                evidence_satisfied=False,
                retry_count=-1,
            )

    def test_negative_retry_budget_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "max_retries"):
            ValidationContext(
                output_valid=False,
                evidence_satisfied=False,
                max_retries=-1,
            )


if __name__ == "__main__":
    unittest.main()
