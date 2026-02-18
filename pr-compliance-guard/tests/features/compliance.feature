Feature: PR Compliance

  Scenario: Valid PR
    Given branch "feature/COM-123-add-check"
    And commit message "COM-123 add validation"
    And PR title "COM-123 Add validation"
    When compliance is evaluated
    Then result should be compliant

  Scenario: Invalid branch
    Given branch "random-branch"
    And commit message "COM-123 update"
    And PR title "COM-123 Update"
    When compliance is evaluated
    Then result should fail
