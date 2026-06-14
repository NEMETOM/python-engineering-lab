Feature: Kafka Client
  create_producer and create_consumer wrap KafkaProducer/KafkaConsumer
  with consistent broker, serialization, and offset configuration.

  Scenario Outline: create_producer connects to the configured broker
    When create_producer is called
    Then the producer bootstrap_servers is "localhost:9092"
    And the producer value_serializer encodes "<key>" as JSON bytes

    Examples:
      | key   |
      | price |
      | order |

  Scenario Outline: create_consumer subscribes to the given topic and group
    When create_consumer is called with topic "<topic>" and group "<group>"
    Then the consumer subscribes to topic "<topic>"
    And the consumer group_id is "<group>"
    And the consumer auto_offset_reset is "earliest"

    Examples:
      | topic            | group            |
      | validated_orders | matching-engine  |
      | trades           | trade-store      |

  Scenario Outline: create_consumer deserializer decodes JSON bytes
    When create_consumer is called with topic "t" and group "g"
    Then the consumer deserializer decodes "<payload>" correctly

    Examples:
      | payload                         |
      | {"order_id": "O1", "price": 1}  |
      | {"symbol": "AAPL"}              |
