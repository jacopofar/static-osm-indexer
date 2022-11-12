import click


def validate_list(ctx, param, value):
    if not isinstance(value, str):
        raise click.BadParameter(f"must be a string, it was {type(value)}")
    try:
        [minlon, minlat, maxlon, maxlat] = value.split(",")
        return tuple(float(v) for v in [minlon, minlat, maxlon, maxlat])
    except ValueError:
        raise click.BadParameter(
            f"format was not minlon, minlat, maxlon, maxlat It was: {value}"
        )
