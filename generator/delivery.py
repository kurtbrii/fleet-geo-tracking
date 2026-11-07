"""Count Kafka delivery outcomes for the generator's per-second report.

Called from: python generator/generator.py → main → run_simulation → DeliveryStats
"""

from dataclasses import dataclass

from confluent_kafka import KafkaError, Message


@dataclass
class DeliveryStats:
    """Delivery outcomes for the current report window.

    Attributes:
        sent: Messages the broker acknowledged. ex: 1000
        failed: Messages that errored or never left the local queue. ex: 0
        last_error: Text of the most recent failure. ex: "Local: Message timed out"
    """

    sent: int = 0
    failed: int = 0
    last_error: str = ""

    def record(self, err: KafkaError | None, msg: Message) -> None:
        """Count one delivery report; librdkafka calls this from poll().

        Args:
            err: None when the broker acknowledged the message. ex: None
            msg: The delivered message (unused). ex: Message(topic="fleet.positions")
        """
        if err is None:
            self.sent += 1
        else:
            self.failed += 1
            self.last_error = err.str()


def report_activity(stats: DeliveryStats, elapsed: float) -> None:
    """Print this window's send and failure rates, then reset the counts.

    Args:
        stats: The window's delivery counts; reset after printing. ex:
            DeliveryStats(sent=0, failed=2000, last_error="Local: Message timed out")
        elapsed: Real seconds the window covered. ex: 2.0

    Returns:
        None; prints one line. ex: "sent 0/s, failed 1000/s (last error: Local: Message timed out)"
    """
    line = f"sent {round(stats.sent / elapsed)}/s, failed {round(stats.failed / elapsed)}/s"
    if stats.failed:
        line += f" (last error: {stats.last_error})"
    print(line, flush=True)
    stats.sent = stats.failed = 0
