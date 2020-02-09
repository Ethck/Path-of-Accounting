import logging

base_graph = dict()
map_graph = dict()

def __add_magic_base(dict_item, words, item_type):
    word = words[0]
    if len(words) == 1:
        dict_item[word] = item_type
    else:
        dict_item[word] = dict()
        __add_magic_base(dict_item[word], words[1:], item_type)

def add_magic_base(item_base, item_type):
    global base_graph
    words = item_base.split(' ')
    logging.debug("Adding magic base: %s" % item_base)
    __add_magic_base(base_graph, words, item_type)

def __get_magic_type(dict_item, words, base=[]):
    if len(words) == 0:
        return None

    word = words[0]
    if word in dict_item:
        base.append(word)
        if isinstance(dict_item[word], dict):
            return __get_magic_type(dict_item[word], words[1:])
        # In this case, it wasn't a dict, so it _must_ be a str, which
        # is the type we're looking for.
        return (' '.join(base), dict_item[word])

    return None

def get_magic_type(line):
    global base_graph
    words = line.split(' ')
    length = len(words)
    result = None
    while length > 0 and result is None:
        result = __get_magic_type(base_graph, words)
        length -= 1
        words = words[1:]
    return result

def __add_map_base(dict_item, words):
    word = words[0]
    if len(words) == 1:
        dict_item[word] = True
    else:
        dict_item[word] = dict()
        __add_map_base(dict_item[word], words[1:])

def add_map_base(map_base):
    global map_graph
    words = map_base.split(' ')
    logging.debug("Adding map base: %s" % map_base)
    __add_map_base(map_graph, words)

def __get_map_base(dict_item, words, base=[]):
    if len(words) == 0:
        return None

    word = words[0]
    if word in dict_item:
        base.append(word)
        if isinstance(dict_item[word], dict):
            return __get_map_base(dict_item[word], words[1:])
        # In this case, it wasn't a dict, so it _must_ be a str, which
        # is the type we're looking for.
        return ' '.join(base)

    return None

def get_map_base(line):
    global map_graph
    words = line.split(' ')
    length = len(words)
    result = None
    while length > 0 and result is None:
        result = __get_map_base(map_graph, words)
        length -= 1
        words = words[1:]
    return result
