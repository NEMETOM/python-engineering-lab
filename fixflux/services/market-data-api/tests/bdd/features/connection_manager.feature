Feature: Broadcasting survives dead connections
  ConnectionManager sends each payload to every tracked WebSocket. A connection
  that fails mid-broadcast is dropped, not raised, so one gone client can never
  stop the others from receiving data.

  Scenario Outline: Dead connections are dropped during a broadcast
    Given a connection manager with <total> connections of which <dead> fail on send
    When a market data payload is broadcast
    Then <alive> connections receive the payload
    And the manager tracks <alive> connections

    Examples:
      | total | dead | alive |
      | 3     | 1    | 2     |
      | 5     | 4    | 1     |
      | 2     | 2    | 0     |
      | 2     | 0    | 2     |
