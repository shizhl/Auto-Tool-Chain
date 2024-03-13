import json

def normalize(sss):
    tmp = [
        '(/documentation/web-api/#spotify-uris-and-ids)',
        '(https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2)',
        '(http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2)',
        '(https://www.spotify.com/se/account/overview/)',
        '<br/>',
        '<br>',
        '\n',
        '/documentation/general/guides/track-relinking-guide/',
        '(http://en.wikipedia.org/wiki/Universal_Product_Code)',
        '(http://en.wikipedia.org/wiki/International_Standard_Recording_Code)',
        '/documentation/web-api/#spotify-uris-and-ids'
    ]
    for s in tmp:
        sss = sss.replace(s, '')
    return sss

def simplify_dict(data):
    """
    Recursively simplify the dictionary by removing specific keys.

    :param data: The input dictionary to be simplified.
    :return: A simplified dictionary with specified keys removed.
    """
    keys_to_remove = ['example', 'nullable', 'x-spotify-docs-type','required']

    if isinstance(data, dict):
        results={}
        for k, v in data.items():
            if k in keys_to_remove:
                continue
            if k == 'description':
                results[k]=normalize(simplify_dict(v))
            else:
                results[k]=simplify_dict(v)
        return  results
    elif isinstance(data, list):
        return [simplify_dict(item) for item in data]
    else:
        return data


# Since the original dictionary was incomplete, I'll demonstrate the function using a smaller example.
# example_data = {
#     'key1': {
#         'example': 'value1',
#         'data': 'value2'
#     },
#     'key2': {
#         'nullable': 'value3',
#         'content': 'value4',
#         'nested': {
#             'x-spotify-docs-type': 'type1',
#             'detail': 'value5'
#         }
#     }
# }

data={'previous': {'description': 'URL to the previous page of items. ( `null` if none)\n', 'example': 'https://api.spotify.com/v1/me/shows?offset=1&limit=1', 'nullable': 'true', 'type': 'string'}, 'items': {'items': {'properties': {'artists': {'description': 'The artists who performed the track. Each artist object includes a link in `href` to more detailed information about the artist.', 'items': {'properties': {'external_urls': {'properties': {'spotify': {'description': 'The [Spotify URL](/documentation/web-api/#spotify-uris-and-ids) for the object.\n', 'type': 'string'}}, 'required': [], 'type': 'object'}, 'href': {'description': 'A link to the Web API endpoint providing full details of the artist.\n', 'type': 'string'}, 'id': {'description': 'The [Spotify ID](/documentation/web-api/#spotify-uris-and-ids) for the artist.\n', 'type': 'string'}, 'name': {'description': 'The name of the artist.\n', 'type': 'string'}, 'type': {'description': 'The object type.\n', 'enum': ['artist'], 'type': 'string'}, 'uri': {'description': 'The [Spotify URI](/documentation/web-api/#spotify-uris-and-ids) for the artist.\n', 'type': 'string'}}, 'type': 'object', 'x-spotify-docs-type': 'SimplifiedArtistObject'}, 'type': 'array'}, 'available_markets': {'description': 'A list of the countries in which the track can be played, identified by their [ISO 3166-1 alpha-2](http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2) code.\n', 'items': {'type': 'string'}, 'type': 'array'}, 'disc_number': {'description': 'The disc number (usually `1` unless the album consists of more than one disc).', 'type': 'integer'}, 'duration_ms': {'description': 'The track length in milliseconds.', 'type': 'integer'}, 'explicit': {'description': 'Whether or not the track has explicit lyrics ( `true` = yes it does; `false` = no it does not OR unknown).', 'type': 'boolean'}, 'external_urls': {'properties': {'spotify': {'description': 'The [Spotify URL](/documentation/web-api/#spotify-uris-and-ids) for the object.\n', 'type': 'string'}}, 'required': [], 'type': 'object'}, 'href': {'description': 'A link to the Web API endpoint providing full details of the track.', 'type': 'string'}, 'id': {'description': 'The [Spotify ID](/documentation/web-api/#spotify-uris-and-ids) for the track.\n', 'type': 'string'}, 'is_local': {'description': 'Whether or not the track is from a local file.\n', 'type': 'boolean'}, 'is_playable': {'description': 'Part of the response when [Track Relinking](/documentation/general/guides/track-relinking-guide/) is applied. If `true`, the track is playable in the given market. Otherwise `false`.\n', 'type': 'boolean'}, 'linked_from': {'properties': {'external_urls': {'properties': {'spotify': {'description': 'The [Spotify URL](/documentation/web-api/#spotify-uris-and-ids) for the object.\n', 'type': 'string'}}, 'required': [], 'type': 'object'}, 'href': {'description': 'A link to the Web API endpoint providing full details of the track.\n', 'type': 'string'}, 'id': {'description': 'The [Spotify ID](/documentation/web-api/#spotify-uris-and-ids) for the track.\n', 'type': 'string'}, 'type': {'description': 'The object type: "track".\n', 'type': 'string'}, 'uri': {'description': 'The [Spotify URI](/documentation/web-api/#spotify-uris-and-ids) for the track.\n', 'type': 'string'}}, 'required': [], 'type': 'object'}, 'name': {'description': 'The name of the track.', 'type': 'string'}, 'preview_url': {'description': 'A URL to a 30 second preview (MP3 format) of the track.\n', 'type': 'string', 'x-spotify-policy-list': [{}]}, 'restrictions': {'properties': {'reason': {'description': "The reason for the restriction. Supported values:\n- `market` - The content item is not available in the given market.\n- `product` - The content item is not available for the user's subscription type.\n- `explicit` - The content item is explicit and the user's account is set to not play explicit content.\n\nAdditional reasons may be added in the future.\n**Note**: If you use this field, make sure that your application safely handles unknown values.\n", 'type': 'string'}}, 'required': [], 'type': 'object'}, 'track_number': {'description': 'The number of the track. If an album has several discs, the track number is the number on the specified disc.\n', 'type': 'integer'}, 'type': {'description': 'The object type: "track".\n', 'type': 'string'}, 'uri': {'description': 'The [Spotify URI](/documentation/web-api/#spotify-uris-and-ids) for the track.\n', 'type': 'string'}}, 'type': 'object', 'x-spotify-docs-type': 'SimplifiedTrackObject'}, 'type': 'array'}}

simplified_data = simplify_dict(data)
print(json.dumps(simplified_data))
