Feature: FIX message types

  Scenario Outline: Parse standard FIX message types
    Given a FIX message with type <msg_type> and fields <fields>
    When the message is parsed
    Then the parsed message type should be <msg_type>

    Examples:
      | msg_type | fields                              |
      | A        | 108=30                              |
      | 0        | 112=TEST                            |
      | D        | 55=AAPL\|44=100\|38=10\|54=1        |
      | 8        | 37=ORD001\|39=2                     |
      | F        | 41=ORD001\|55=AAPL                  |

  Scenario: Serialize and round-trip a NewOrderSingle
    Given a NewOrderSingle message for symbol AAPL price 100 quantity 10
    When the message is serialized and parsed back
    Then the round-trip message type should be D
    And the round-trip symbol should be AAPL

  Scenario: Serialize and round-trip an ExecutionReport
    Given an ExecutionReport for order ORD001 with status 2
    When the message is serialized and parsed back
    Then the round-trip message type should be 8
    And the round-trip order id should be ORD001
