from sly import Lexer, Parser
from pprint import pprint
import datetime


class My1CLexer(Lexer):
    tokens = {ID, EQ, NUM, SCOL, STR,
              PROC, ENDPROC, LB, RB,
              COMMA, IF, ELSE, ELSEIF, THEN, END,
              GT, LT, NEQ, QMARK,
    }
    ID[r'Процедура'] = PROC
    ID[r'КонецПроцедуры'] = ENDPROC
    ID[r'Если'] = IF
    ID[r'Иначе'] = ELSE
    ID[r'ИначеЕсли'] = ELSEIF
    ID[r'Тогда'] = THEN
    ID[r'КонецЕсли'] = END
    GT = r'>'
    LT = r'<'
    NEQ = r'<>'
    QMARK = r'\?'
    LB = r'\('
    RB = r'\)'
    EQ = r'='
    SCOL = r';'
    COMMA = r','
    # Игнорируются пробельные символы и комментарии
    ignore = ' \t'
    ignore_spaces = r' |\t|\n'
    ignore_comment = r'//.*'

    # Обработка слов
    @_(r'[a-zA-Zа-яА-Я_][a-zA-Zа-яА-Я_0-9]*')
    def ID(self, token):
        token.value = (token.value.lower())
        return token

    # Обработка строк
    @_(r'("[^"]*")|(\'[^\']*\')')
    def STR(self, token):
        token.value = token.value.lower()[1:-1]
        return token

    # Обработка чисел
    @_(r'[0-9]+')
    def NUM(self, token):
        token.value = int(token.value)
        return token

    # Обработка ошибок
    def error(self, t):
        print(f"Некорректный символ '{t.value[0]}' в строке {self.lineno}")
        self.index += 1


class My1CParser(Parser):
    tokens = My1CLexer.tokens

    @_('{ procedure } { statement }')
    def block(self, p):
        return ('block', p.procedure, p.statement)

    # Процедура МояПроцедура ( параметры ) блок КонецПроцедуры
    @_('PROC ID LB parameters RB block ENDPROC')
    def procedure(self, p):
        return ('proc', p.ID, p.parameters, p.block)

    # Параметр1 ,Параметр2 ,Параметр3
    @_('ID { COMMA ID }')
    def parameters(self, p):
        return [p.ID0] + p.ID1

    # Параметры отсутствуют.
    @_('')
    def parameters(self, p):
        return []

    # ( "Значение" ,42 ,43 )
    @_('value { COMMA value }')
    def arguments(self, p):
        return [p.value0] + p.value1

    # Аргументы отсутствуют.
    @_('')
    def arguments(self, p):
        return []

    # A = value ;
    @_('ID EQ value SCOL')
    def statement(self, p):
        return ('assign', p.ID, p.value)

    # Сообщить ( аргументы ) ;
    @_('ID LB arguments RB SCOL')
    def statement(self, p):
        return ('call', p.ID, p.arguments)

    # МояПроцедура
    @_('ID')
    def value(self, p):
        return ('var', p.ID)

    # 42
    @_('NUM')
    def value(self, p):
        return ('number', p.NUM)

    # "Hello"
    @_('STR')
    def value(self, p):
        return ('str', p.STR)

    # Сообщить ( аргументы ) ;
    @_('ID LB arguments RB')
    def value(self, p):
        return ('call', p.ID, p.arguments)

    # Оператор больше
    @_('value GT value')
    def value(self, p):
        return ('gt', p.value0, p.value1)

    # Оператор не равно
    @_('value NEQ value')
    def value(self, p):
        return ('neq', p.value0, p.value1)

    # тернарный оператор '?'
    @_('QMARK value QMARK value QMARK value')
    def value(self, p):
        return ('qmark', p.value0, p.value1, p.value2)

    # Оператор меньше
    @_('value LT value')
    def value(self, p):
        return ('lt', p.value0, p.value1)

    # если <значение> тогда <блок> КонецЕсли;
    @_('IF value THEN block END SCOL')
    def statement(self, p):
        return ('if', p.value, p.block, None)

    # иначеесли <значение> тогда <блок> КонецЕсли;
    @_('ELSEIF value THEN block END SCOL')
    def statement(self, p):
        return ('elseif', p.value, p.block, None)

    # иначеесли тогда <блок> КонецЕсли;
    @_('ELSE value THEN block END SCOL')
    def statement(self, p):
        return ('else', p.block, None)

    # Обработка ошибок
    def error(self, p):
        if p:
            print(f"Синтаксическая ошибка в строке {self.lexer.lineno}. "f"Ожидалось: {p.type}. Получено: {p.value}")
        else:
            print("Непредвиденная ошибка")


def interpret(env, ast):
    spec, *args = ast
    if spec == "block":
        procs = args[0]
        statements = args[1]
        for proc in procs + statements:
            interpret(env, proc)
    elif spec == "proc":
        name, params, stmts = args
        env[name] = (params, stmts)
    elif spec == "if":
        condition, yes, no = args
        if interpret(env, condition):
            interpret(env, yes)
    elif spec == "end":
        condition, yes, no = args
        if interpret(env, condition):
            interpret(env, yes)
    elif spec == "else":
        condition, yes, no = args
        if interpret(env, condition):
            interpret(env, yes)
    elif spec == "gt":
        left, right = args
        return interpret(env, left) > interpret(env, right)
    elif spec == "neq":
        left, right = args
        return interpret(env, left) != interpret(env, right)
    elif spec == "qmark":
        condition, yes, no = args
        if interpret(env, condition):
            return interpret(env, yes)
        else:
            return interpret(env, no)
    elif spec == "lt":
        left, right = args
        return interpret(env, left) < interpret(env, right)
    elif spec == "assign":
        name, value = args
        env[name] = interpret(env, value)
    elif spec == "call":
        name, values = args
        function = env[name]
        if isinstance(function, tuple):
            params, stmts = function
            local = env.copy()
            for i in range(len(params)):
                name = params[i]
                value = values[i]
                local[name] = interpret(env, value)
            return interpret(local, stmts)
        else:
            params = [interpret(env, a) for a in values]
            return function(*params)
    elif spec == "var":
        return env[args[0]]
    elif spec in ("number", "str"):
        return args[0]


code = '''
Процедура МояПроцедура(ВтороеСообщение)
Если 1 < 2 Тогда
    Сообщить("Один равен нулю.");
КонецЕсли;
КонецПроцедуры
A = 42; // Это – комментарий
a = 24;
ПримерПеременной = "Добрый день, 1С!";
ПустаяСтрока = "";
Сообщить(ПримерПеременной);
Сообщить(A);
МояПроцедура("Данные удалены.");
// дата = ТекущаяДата();
Сообщить(ТекущаяДата());
Сообщить(ДеньНедели(ТекущаяДата()));

'''


lexer = My1CLexer()
parser = My1CParser()


# Лексический анализ (токенизация).
tokens = list(lexer.tokenize(code))
print("\nТокены:")
pprint(tokens)

# Синтаксический анализ
# (построение дерева синтаксиса).
tree = parser.parse(iter(tokens))
print("\nДерево:")
pprint(tree)


def message(text):
    print(text)


# Интерпретация дерева синтаксиса.
print("\nВывод:")
env = {
    "сообщить": message,
    "текущаядата": lambda: datetime.datetime.now(),
    "деньнедели": lambda date: date.weekday()+1
}
interpret(env, tree)
