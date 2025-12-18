---
name: "python-documentation"
applyTo: "**/*.py"
---

# Padrão de documentação e boas práticas para Python

Este documento define o padrão obrigatório para docstrings, tipagem e comentários em todos os arquivos Python deste projeto.

## Padrão de docstring

Cada função, método ou classe deve conter uma docstring no início do bloco, seguindo o formato abaixo:

```python
"""
<Descreva de forma breve e imperativa o objetivo da função.>

Args:
	<param1> (<tipo>): <descrição clara do parâmetro>
	<param2> (<tipo>): <descrição clara do parâmetro>

Returns:
	<tipo>: <descrição objetiva do valor retornado>

Raises:
	<TipoDeExcecao>: <quando e por que a exceção é lançada> (opcional)
"""
```

### Exemplo correto

```python
def soma(a: int, b: int) -> int:
	"""
	Retorne a soma de dois inteiros.

	Args:
		a (int): Primeiro número.
		b (int): Segundo número.

	Returns:
		int: Resultado da soma.
	"""
	return a + b
```

### Exemplo incorreto

```python
def soma(a, b):
	"Soma dois números."
	return a + b
```

## Regras detalhadas

- **Docstring do zero:** Sempre escreva a docstring do zero ao corrigir ou criar funções/classes. Não copie docstrings antigas.
- **Idioma:** O texto da docstring deve ser sempre em português.
- **Limite de caracteres:** Cada linha da docstring deve ter no máximo 65 caracteres para facilitar a leitura.
- **Modo imperativo:** O sumário (primeira linha) deve começar com verbo no imperativo (ex: "Retorne", "Calcule", "Obtenha").
- **Nome das funções e variáveis:** Utilize nomes descritivos e claros, preferencialmente em inglês.
- **Tipagem obrigatória:** Sempre adicione tipagem explícita para todos os parâmetros e para o retorno das funções. Exemplo: `def foo(a: int) -> str:`
- **Evite Any built-in do python e do Typing:** Não utilize o tipo `Any` diretamente do módulo `typing`.
  Caso seja necessário, crie um alias: `type AnyType = Any`.
- **Sem Raises/Returns para funções void:** Se a função não retorna nada, não inclua as seções `Returns` ou `Raises` na docstring.

## Justificativas

- **Clareza:** Docstrings detalhadas facilitam o entendimento e manutenção do código.
- **Padronização:** O uso de um padrão único melhora a colaboração entre desenvolvedores.
- **Ferramentas:** Docstrings bem formatadas são aproveitadas por ferramentas de documentação automática.
- **Tipagem:** Tipos explícitos ajudam a evitar erros e facilitam o uso de linters e IDEs.

## Exemplos de comentários explicativos

```python
# Calcula o fatorial de um número inteiro de forma recursiva
def fatorial(n: int) -> int:
	"""
	Calcule o fatorial de um número inteiro.

	Args:
		n (int): Número para calcular o fatorial.

	Returns:
		int: Fatorial de n.
	"""
	if n == 0:
		return 1
	return n * fatorial(n - 1)
```

## Observações finais

- Sempre revise docstrings e comentários ao revisar código.
- Prefira nomes de variáveis e funções descritivos.
- Utilize comentários para separar blocos lógicos complexos.
