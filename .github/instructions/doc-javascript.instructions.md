---
applyTo: "**/*.ts, **/*.js"
---

# Documentação js/ts

Este documento define regras **obrigatórias** para geração de código
JavaScript e TypeScript utilizando GitHub Copilot. O objetivo é garantir
padronização, legibilidade, tipagem explícita e documentação consistente.

---

## 1. Regra Absoluta: Sempre usar JSDoc

Toda função, método, classe e interface **DEVE** possuir comentário JSDoc.
Nunca deixe código público ou exportado sem documentação.

Formato obrigatório:

```js
/**
 * <Resumo da função no modo imperativo>
 *
 * @param {Tipo} nome - Descrição do parâmetro.
 * @returns {Tipo} Descrição do retorno.
 * @throws {TipoErro} Descrição do erro (se existir).
 */
```

---

## 2. Idioma

- A documentação **DEVE SER EM PORTUGUÊS**.
- Evite termos em inglês quando houver equivalente técnico.
- Exemplo:
  - ✅ "Carregar arquivo"
  - ❌ "Load file"

---

## 3. Estilo do Sumário

O resumo deve seguir as regras:

- Primeira frase no **modo imperativo**
- Máximo de **65 caracteres por linha**
- Não mencionar "função", "método" ou "classe"

Exemplos:

✅ Correto:

```js
/**
 * Calcular valor total do pedido.
 */
```

❌ Incorreto:

```js
/**
 * Esta função calcula o valor.
 */
```

---

## 4. Tipagem é Obrigatória

### JavaScript

Todos os parâmetros e retornos devem ser tipados via JSDoc:

```js
/**
 * Converter texto para número.
 *
 * @param {string} valor - Texto de entrada.
 * @returns {number} Número convertido.
 */
function parse(valor) {
  return Number(valor);
}
```

### TypeScript

Mesmo com TypeScript, o JSDoc **não é opcional**:

```ts
/**
 * Somar dois números.
 *
 * @param {number} a - Primeiro operando.
 * @param {number} b - Segundo operando.
 * @returns {number} Resultado da soma.
 */
function somar(a: number, b: number): number {
  return a + b;
}
```

---

## 5. Proibição de `any`

Nunca usar:

- `any`
- `Object`
- `Function`

### Substituição recomendada:

```ts
type AnyType = unknown;
```

Uso correto:

```ts
/**
 * Processar valor genérico.
 *
 * @param {unknown} valor - Dado sem tipo definido.
 * @returns {unknown} Resultado do processamento.
 */
```

---

## 6. Funções Sem Retorno

Se a função não retorna valor real:

- Não usar `@returns`
- Não usar `@throws`

Exemplo correto:

```js
/**
 * Registrar mensagem no console.
 *
 * @param {string} msg - Texto exibido.
 */
function log(msg) {
  console.log(msg);
}
```

---

## 7. Tratamento de Erros

Somente documentar erros realmente lançados:

```js
/**
 * Dividir números.
 *
 * @param {number} a - Dividendo.
 * @param {number} b - Divisor.
 * @returns {number} Resultado.
 * @throws {Error} Se divisor for zero.
 */
function dividir(a, b) {
  if (b === 0) {
    throw new Error("Divisão por zero");
  }
  return a / b;
}
```

---

## 8. Código sem Comentário é Erro

Se não houver documentação:

- O Copilot deve criar o JSDoc completo.
- Nunca deixar bloco sem explicação.

---

## 9. Regras para Classes

### Obrigatório:

- JSDoc na classe
- JSDoc em cada método público
- Tipagem explícita

Exemplo:

```ts
/**
 * Controlar autenticação do usuário.
 */
class AuthService {
  /**
   * Validar credenciais informadas.
   *
   * @param {string} login - Identificador.
   * @param {string} senha - Senha.
   * @returns {boolean} Resultado da validação.
   */
  validar(login: string, senha: string): boolean {
    return true;
  }
}
```

---

## 10. Padrão de Nomes

- Funções: camelCase
- Classes: PascalCase
- Constantes: UPPER_SNAKE_CASE
- Interfaces: IInterface

---

## 11. Regras de Organização

- Uma função = uma responsabilidade
- Evitar funções com mais de 30 linhas
- Evitar parâmetros em excesso (> 5)

---

## 12. Regra Final

O Copilot deve:

- Gerar documentação sempre
- Nunca usar any
- Nunca omitir tipo
- Priorizar clareza a otimização
- Não ultrapassar 65 caracteres por linha
