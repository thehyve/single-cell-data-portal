import boto3
import requests
import typing
from abc import ABC, abstractmethod
from urllib.parse import urlparse, ParseResult


class MissingHeaderException(Exception):
    def __init__(self, detail: str = "", *args, **kwargs) -> None:
        self.detail = "Missing header from response. " + detail


# TODO: consider renaming as URI
class URL(ABC):
    """Define the abstract base class to support different download sources."""

    def __init__(self, url, parsed_url: ParseResult):
        self.url: str = url
        self.parsed_url: ParseResult = parsed_url

    @classmethod
    @abstractmethod
    def validate(cls, url: str) -> typing.Optional["URL"]:
        """Validates the URL matches the expected format, and returns a new class object if valid.."""
        pass

    @abstractmethod
    def file_info(self) -> dict:
        """
        Extract information about a file from a URL.
        """
        pass

    @property
    def scheme(self):
        return self.parsed_url.scheme

    @property
    def netloc(self):
        return self.parsed_url.netloc

    @property
    def path(self):
        return self.parsed_url.path

    def _get_key(self, headers: dict, key: str) -> str:
        try:
            return headers[key]
        except KeyError:
            raise MissingHeaderException(
                f"{self.__class__.__name__}:URL({self.url}) failed request. '{key}' not present in the header."
            )

    def _get_key_with_fallback(self, headers: dict, key: str, fallback_key: str) -> str:
        try:
            return headers.get(key) or headers[fallback_key]
        except KeyError:
            raise MissingHeaderException(
                f"""{self.__class__.__name__}:URL({self.url}) failed request.
                Neither '{key}' nor '{fallback_key}' are present in the header.
                """
            )


class DropBoxURL(URL):
    """Supports download URLs from a DropBox share link."""

    @classmethod
    def validate(cls, url: str) -> typing.Optional["URL"]:
        """Converts a valid DropBox URL into a direct download link. If the url is not a valid DropBox URL, none is
        returned. Otherwise, the converted URL is returned.
        """

        parsed_url = urlparse(url)
        if parsed_url.scheme != "https" or parsed_url.netloc != "www.dropbox.com":
            return None
        # dl=0 will show the file in the preview page. A link with ? dl=1 will force the file to download.
        if "dl=0" in parsed_url.query:
            new_query = parsed_url.query.replace("dl=0", "dl=1")
        elif not parsed_url.query:
            new_query = "dl=1"
        elif "dl=1" in parsed_url.query:
            new_query = parsed_url.query
        else:
            new_query = parsed_url.query + "&dl=1"

        parsed_url = parsed_url._replace(query=new_query)
        return cls(parsed_url.geturl(), parsed_url)

    def file_info(self) -> dict:
        """
        Extract information about a file from a DropBox URL.
        :param url: a DropBox URL leading to a file.
        :return: The file name and size of the file.
        """
        resp = requests.head(self.url, allow_redirects=True)
        resp.raise_for_status()

        try:
            size = int(self._get_key_with_fallback(resp.headers, "content-length", "x-dropbox-content-length"))
        except Exception:
            size = None

        return {
            "size": size,
            "name": self._get_key(resp.headers, "content-disposition").split(";")[1].split("=", 1)[1][1:-1],
        }


class S3URL(URL):
    """Supports presigned URLs from an AWS S3 bucket."""

    _netloc = "s3.amazonaws.com"
    _scheme = "https"

    @classmethod
    def validate(cls, url: str):
        parsed_url = urlparse(url)
        return (
            cls(url, parsed_url)
            if parsed_url.scheme == cls._scheme and parsed_url.netloc.endswith(cls._netloc)
            else None
        )

    def file_info(self) -> dict:
        resp = requests.get(self.url, headers={"Range": "bytes=0-0"})
        resp.raise_for_status()

        return {
            "size": int(self._get_key(resp.headers, "content-range").split("/")[1]),
            "name": self.parsed_url.path,
        }


class S3URI(URL):
    """
    Handles S3 URIs: s3://<bucket>/<key>
    """

    @classmethod
    def validate(cls, url: str) -> typing.Optional["URL"]:
        parsed = urlparse(url)
        bucket_name = parsed.netloc
        key = parsed.path
        if parsed.scheme == "s3" and bucket_name and key:
            return cls(parsed.geturl(), parsed)
        else:
            return None

    def file_info(self) -> dict:
        s3 = boto3.resource("s3")
        s3_object = s3.Object(self.bucket_name, self.key)
        return {"name": self.key, "size": s3_object.content_length}

    @property
    def bucket_name(self):
        return self.parsed_url.netloc

    @property
    def key(self):
        return self.parsed_url.path


class RegisteredSources:
    """Manages all of the download sources."""

    _registered = set()

    @classmethod
    def add(cls, parser: typing.Type[URL]):
        if issubclass(parser, URL):
            cls._registered.add(parser)
        else:
            raise TypeError(f"subclass type {URL.__name__} expected")

    @classmethod
    def remove(cls, parser: typing.Type[URL]):
        cls._registered.remove(parser)

    @classmethod
    def get(cls) -> typing.Iterable:
        return cls._registered


def from_url(url: str) -> URL:
    """Given a URL return a object that can be used by the processing container to download data."""
    for source in RegisteredSources.get():
        url_obj = source.validate(url)
        if url_obj:
            return url_obj


# RegisteredSources are processed in the order registered and returns the first match.
RegisteredSources.add(DropBoxURL)
RegisteredSources.add(S3URL)
RegisteredSources.add(S3URI)
