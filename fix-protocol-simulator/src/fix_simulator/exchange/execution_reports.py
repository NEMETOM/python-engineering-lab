#fix-protocol-simulator/src/fix_simulator/exchange/execution_reports.py

from fix_simulator.protocol.fix_message import FixMessage


class ExecutionReportFactory:

    @staticmethod
    def create(order_id, status):

        fields = {
            "35": "8",
            "37": order_id,
            "39": status
        }

        return FixMessage(fields)