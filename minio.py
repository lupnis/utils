from aiobotocore.session import get_session
from typing import Optional


class MinioUtils(object):
    def __init__(self, endpoint_url: str, access_key: str, secret_key: str, bucket_name: str):
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name

    async def read_file(self, object_name: str, bucket_name: Optional[str] = None):
        if not bucket_name:
            bucket_name = self.bucket_name
        session = get_session()
        async with session.create_client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key
        ) as client:
            response = await client.get_object(Bucket=bucket_name, Key=object_name)
            async with response["Body"] as stream:
                data = await stream.read()
            return data
