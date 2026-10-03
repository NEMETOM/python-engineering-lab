Feature: FIX Gateway message handling and session management

  Scenario Outline: Identify FIX message types
    Given a parsed FIX message with type "<msg_type>"
    Then the handler identifies it as "<label>"

    Examples:
      | msg_type | label     |
      | A        | logon     |
      | 0        | heartbeat |
      | D        | new order |
      | 5        | logout    |

  Scenario: Parse a raw FIX Logon message
    Given a raw FIX message "35=A|49=CLIENT1|108=30|"
    When the message is parsed
    Then the parsed field "35" equals "A"
    And the parsed field "49" equals "CLIENT1"

  Scenario: Parse a raw FIX NewOrderSingle message
    Given a raw FIX message "35=D|49=CLIENT1|55=BTCUSD|54=1|44=50000|38=1|"
    When the message is parsed
    Then the parsed field "35" equals "D"
    And the parsed field "55" equals "BTCUSD"
    And the parsed field "54" equals "1"

  Scenario: Fields without a value are ignored during parsing
    Given a raw FIX message "35=D|BADFIELD|55=BTCUSD|"
    When the message is parsed
    Then the parsed field "35" equals "D"
    And the parsed field "55" equals "BTCUSD"

  Scenario: Create a new session on Logon
    Given a session manager
    When a logon is received from sender "CLIENT1"
    Then a session exists for "CLIENT1"

  Scenario: Heartbeat updates the session timestamp
    Given a session manager
    And a session already exists for sender "CLIENT2"
    When a heartbeat is received from sender "CLIENT2"
    Then the last heartbeat for "CLIENT2" is recent

  Scenario: Unknown sender heartbeat does not raise an error
    Given a session manager
    When a heartbeat is received from sender "UNKNOWN"
    Then no session exists for "UNKNOWN"

  Scenario: A session that has gone silent past the timeout is expired
    Given a session manager
    And a session already exists for sender "CLIENT3"
    And the last heartbeat for "CLIENT3" was 61 seconds ago
    Then the session for "CLIENT3" is expired with a 60 second timeout

  Scenario: A session that heartbeats within the timeout is not expired
    Given a session manager
    And a session already exists for sender "CLIENT4"
    And the last heartbeat for "CLIENT4" was 10 seconds ago
    Then the session for "CLIENT4" is not expired with a 60 second timeout

  Scenario: An unknown sender is never considered expired
    Given a session manager
    Then the session for "UNKNOWN" is not expired with a 60 second timeout
