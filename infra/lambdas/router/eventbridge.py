import boto3

_events = boto3.client("events")


def publish(bus_name: str, source: str, detail_type: str, detail: str) -> bool:
    result = _events.put_events(
        Entries=[
            {
                "EventBusName": bus_name,
                "Source": source,
                "DetailType": detail_type,
                "Detail": detail,
            }
        ]
    )
    return result.get("FailedEntryCount", 0) == 0
