"""Where a run's files live: local project files or an S3 bucket, chosen by PICKEM_STORAGE.

Files are addressed by key (`cache/pickem.html`, `out/readout.html`, `out/csv/...`). The saved
Pickem session is separate: a local file, or a read-only SSM parameter in S3 mode.
"""
import os

STORAGE_VAR = 'PICKEM_STORAGE'
BUCKET_VAR = 'PICKEM_BUCKET'
MODES = ('local', 's3')

LOCAL_SESSION_FILE = 'resources/pickem_auth.json'
SESSION_PARAMETER = '/pickemplug/pickem-auth'

CONTENT_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.csv': 'text/csv; charset=utf-8',
    '.json': 'application/json',
}
DEFAULT_CONTENT_TYPE = 'text/plain; charset=utf-8'


class LocalBackend:
    mode = 'local'

    def __init__(self, root='.'):
        self.root = root

    def path(self, key):
        """`cache/` keys live in resources/; every other key is the same relative path."""
        if key.startswith('cache/'):
            key = 'resources/' + key[len('cache/'):]
        return os.path.join(self.root, key)

    def read_text(self, key):
        try:
            with open(self.path(key), encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            raise FileNotFoundError(f'No saved data at {key!r} ({self.path(key)})') from None

    def write_text(self, key, text):
        path = self.path(key)
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, 'w', encoding='utf-8', newline='') as file:
            file.write(text)

    def read_session(self):
        try:
            with open(os.path.join(self.root, LOCAL_SESSION_FILE), encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            return None

    def write_session(self, text):
        self.write_text(LOCAL_SESSION_FILE, text)
        return True


class S3Backend:
    mode = 's3'

    def __init__(self, bucket, s3_client=None, ssm_client=None):
        # boto3 is only needed in S3 mode; Lambda's runtime provides it, local runs don't need it.
        try:
            import boto3
        except ImportError as err:
            raise RuntimeError(f'{STORAGE_VAR}=s3 needs boto3, which is not installed') from err
        self.bucket = bucket
        self.s3 = s3_client or boto3.client('s3')
        self.ssm = ssm_client or boto3.client('ssm')

    def read_text(self, key):
        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=key)
        except self.s3.exceptions.NoSuchKey:
            raise FileNotFoundError(f'No saved data at {key!r} (s3://{self.bucket}/{key})') from None
        return response['Body'].read().decode('utf-8')

    def write_text(self, key, text):
        content_type = CONTENT_TYPES.get(os.path.splitext(key)[1].lower(), DEFAULT_CONTENT_TYPE)
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=text.encode('utf-8'),
                           ContentType=content_type, CacheControl='no-cache')

    def read_session(self):
        try:
            response = self.ssm.get_parameter(Name=SESSION_PARAMETER, WithDecryption=True)
        except self.ssm.exceptions.ParameterNotFound:
            return None
        return response['Parameter']['Value']

    def write_session(self, text):
        """The SSM session is populated outside the app; never write it."""
        return False


_backend = None


def _build_backend():
    mode = os.environ.get(STORAGE_VAR, '').strip().lower() or 'local'
    if mode not in MODES:
        raise RuntimeError(f'{STORAGE_VAR} must be one of {", ".join(MODES)}; got {mode!r}')
    if mode == 'local':
        return LocalBackend()
    bucket = os.environ.get(BUCKET_VAR, '').strip()
    if not bucket:
        raise RuntimeError(f'{STORAGE_VAR}=s3 needs the bucket name in {BUCKET_VAR}')
    return S3Backend(bucket)


def backend():
    """The backend for this process, built from the environment on first use."""
    global _backend
    if _backend is None:
        _backend = _build_backend()
    return _backend


def validate():
    """Fail fast on a bad storage configuration, before anything is fetched."""
    backend()


def reset(new_backend=None):
    """Drop the cached backend (re-read the environment on next use), or install a given one."""
    global _backend
    _backend = new_backend


def read_text(key):
    return backend().read_text(key)


def write_text(key, text):
    backend().write_text(key, text)


def read_session():
    """The saved Pickem session document as text, or None if there isn't one."""
    return backend().read_session()


def write_session(text):
    """Save the Pickem session. Returns False when the active storage doesn't accept writes (S3 mode)."""
    return backend().write_session(text)
