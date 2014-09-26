def dict_walk(node, action, match='$ref'):
    if len(node.keys()) == 1 and match in node:
        return action(node[match])
    else:
        newdict = {}
        for key, value in node.items():
            if isinstance(value, dict):
                value = dict_walk(node=value, action=action, match=match)
            if isinstance(value, list):
                value = [
                    dict_walk(node=entry, action=action, match=match)
                    if isinstance(entry, dict) else entry
                    for entry in value
                ]
            newdict[key] = value
        return newdict


def get_ref_path_for_ref_url(url):
    if not url.startswith('#/'):
        raise ValueError('Only local references allowed')
    return url.lstrip('#/').split('/')


def get_ref_definition(schema, matched_value):
    ref_path = get_ref_path_for_ref_url(matched_value)
    # traverse path down or raise exception
    found_definition = schema
    for component in ref_path:
        found_definition = found_definition[component]
    return found_definition


def preprocess_ref(schema):
    def replace_ref_with_definition(matched_value):
        return get_ref_definition(schema, matched_value=matched_value)
    return dict_walk(
        node=schema,
        action=replace_ref_with_definition
    )
