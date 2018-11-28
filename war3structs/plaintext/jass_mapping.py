from lark import (
  Tree as BaseTree,
  Token,
  Transformer
)


#
# These are lazy mappings. They are just the normal trees generated by
# lark but with getters and setters that deal with abstracting their
# children. Getters that return single tokens will never have a setter,
# the token reference itself is modified instead. Getters that return
# many nodes should have a setter.
#
# It's a developer's responsibility to know these properties are
# merely convenience functions and come with all the same overhead.
#
# TODO: Don't be lazy and create full-fledged structures out of all
#       JASS nodes. It will properly abstract a script and reduce the
#       memory footprint by cutting the cruft. (A 26K LOC script's tree
#       currently takes around 70MB.)
#


class Tree(BaseTree):
  """Tree class that all trees inherit from"""

  def find(self, predicate):
    return (node for node in self.children if predicate(node))

  def find_token_pair(self, token_type, offset=1):
    for index, node in enumerate(self.children):
      if isinstance(node, Token) and node.type == token_type:
        return [node, self.children[index+offset]]

    return None

  def find_all(self, type_or_rule):
    return self.find(lambda n: n.type == type_or_rule if isinstance(n, Token) else n.data == type_or_rule)

  def find_first(self, type_or_rule):
    return next(self.find_all(type_or_rule), None)


class WithFuncDeclr():
  """Common properties for function declarations"""

  def _get_declr(self):
    return self.children[1] if not self.is_constant else self.children[2]

  @property
  def id(self):
    return self._get_declr().children[0]

  @property
  def is_constant(self):
    return self.children[0].type == 'CONSTANT'

  @property
  def takes(self):
    declr = self._get_declr()
    args_stop = len(declr.children) - 2

    if args_stop == 3:
      # this is "takes nothing"
      return []

    args = []
    for i in range(2, args_stop, 3):
      args.append([declr.children[i], declr.children[i+1]])

    return args

  @takes.setter
  def takes(self, value):
    declr = self._get_declr()
    args_stop = len(declr.children) - 2
    new_children = declr.children[:2]

    if len(value) == 0:
      new_children.append(Token('NOTHING', 'nothing'))
    else:
      for arg in value:
        new_children.extend(arg + [Token('COMMA', ',')])

      new_children.pop()

    new_children += declr.children[args_stop:]
    declr.children = new_children

  @property
  def returns(self):
    returns = self._get_declr().children[-1]

    if returns.type == 'NOTHING':
      return None

    return returns


class WithVarDeclr():
  """Common properties for variable declarations"""

  @property
  def is_array(self):
    return self.children[-2].type == 'ARRAY'

  @property
  def value(self):
    equals = self.find_token_pair('EQUALS')

    if equals is None:
      return None

    return equals[1]


class TypeTree(Tree):
  """Properties for type declarations"""

  @property
  def id(self):
    return self.children[1]

  @property
  def extends(self):
    return self.children[3]


class NativeTree(Tree, WithFuncDeclr):
  """Properties for native function declarations"""
  pass


class GlobalTree(Tree, WithVarDeclr):
  """Properties for global variable declarations"""

  @property
  def id(self):
    if self.is_constant or self.is_array:
      return self.children[2]

    return self.children[1]

  @property
  def type(self):
    if self.is_constant:
      return self.children[1]

    return self.children[0]

  @property
  def is_constant(self):
    return self.children[0].type == 'CONSTANT'


class LocalTree(Tree, WithVarDeclr):
  """Properties for local variable declarations"""

  @property
  def id(self):
    if self.is_array:
      return self.children[3]

    return self.children[2]

  @property
  def type(self):
    return self.children[1]


class FunctionTree(Tree, WithFuncDeclr):
  """Properties for functions"""

  @property
  def locals(self):
    lls = self.children[3] if not self.is_constant else self.children[4]

    return list(lls.find_all('local_var_declr'))

  @locals.setter
  def locals(self, value):
    lls = self.children[3] if not self.is_constant else self.children[4]
    new_lls = []
    for ll in value:
      new_lls.append(ll)
      new_lls.append(Token('NEWLINE', '\n'))
    lls.children = new_lls

  @property
  def statements(self):
    stms = self.children[4] if not self.is_constant else self.children[5]

    return list(stms.find(lambda n: not isinstance(n, Token)))

  @statements.setter
  def statements(self, value):
    stms = self.children[4] if not self.is_constant else self.children[5]
    new_stms = []
    for stm in value:
      new_stms.append(stm)
      new_stms.append(Token('NEWLINE', '\n'))
    stms.children = new_stms


class ScriptTree(Tree):
  """Properties for the root script"""

  def rebuild_tree(self, types, natives, globals, functions):
    tns = []
    for tn in types + natives:
      tns.append(tn)
      tns.append(Token('NEWLINE', '\n'))

    gs = GlobalTree('globals', [])
    gs.children.append(Token('GLOBALS', 'globals'))
    gs.children.append(Token('NEWLINE', '\n'))
    for g in globals:
      gs.children.append(g)
      gs.children.append(Token('NEWLINE', '\n'))
    gs.children.append(Token('ENDGLOBALS', 'endglobals'))

    fs = []
    for f in functions:
      fs.append(f)
      fs.append(Token('NEWLINE', '\n'))

    self.children = tns + [gs] + fs

  @property
  def types(self):
    return list(self.find_all('type_declr'))

  @types.setter
  def types(self, value):
    self.rebuild_tree(value, self.natives, self.globals, self.functions)

  @property
  def natives(self):
    return list(self.find_all('native_func_declr'))

  @natives.setter
  def natives(self, value):
    self.rebuild_tree(self.types, value, self.globals, self.functions)

  @property
  def globals(self):
    all_declrs = []

    for declrs in self.find_all('globals'):
      all_declrs.extend(declrs.find_all('global_var_declr'))

    return list(all_declrs)

  @globals.setter
  def globals(self, value):
    self.rebuild_tree(self.types, self.natives, value, self.functions)

  @property
  def functions(self):
    return list(self.find_all('func'))

  @functions.setter
  def functions(self, value):
    self.rebuild_tree(self.types, self.natives, self.globals, value)


class MapperTransformer(Transformer):
  """MapperTransformer class

  A transformer that replaces the plain tree of select rules with our
  desired one.
  """

  def start(self, children):
    return ScriptTree('start', children)

  def type_declr(self, children):
    return TypeTree('type_declr', children)

  def native_func_declr(self, children):
    return NativeTree('native_func_declr', children)

  def global_var_declr(self, children):
    return GlobalTree('global_var_declr', children)

  def local_var_declr(self, children):
    return LocalTree('local_var_declr', children)

  def func(self, children):
    return FunctionTree('func', children)