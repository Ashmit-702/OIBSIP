"""Custom exceptions for the weather service.

Keeping these separate from generic exceptions lets the Flask layer map
each failure mode to the right HTTP status and a message that's actually
useful to whoever is calling the API — instead of a single generic 500.
"""


class WeatherServiceError(Exception):
    """Base class for all weather-service failures."""
    status_code = 502  # bad gateway: upstream (OpenWeatherMap) misbehaved


class CityNotFoundError(WeatherServiceError):
    """Raised when OpenWeatherMap can't resolve the requested place."""
    status_code = 404


class InvalidAPIKeyError(WeatherServiceError):
    """Raised when OpenWeatherMap rejects our API key."""
    status_code = 401


class UpstreamTimeoutError(WeatherServiceError):
    """Raised when a request to OpenWeatherMap times out."""
    status_code = 504
