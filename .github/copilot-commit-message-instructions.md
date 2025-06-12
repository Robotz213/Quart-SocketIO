Ao gerar mensagens de commit, o Copilot deve sugerir um título breve, descritivo e no imperativo, indicando resumidamente a principal alteração realizada. No corpo (body) da mensagem de commit, o Copilot deve detalhar separadamente as alterações feitas em cada arquivo modificado, listando o nome do arquivo seguido de uma breve descrição da mudança correspondente. Por exemplo:

Corrige bug na validação de login

src/login.js: Ajusta a lógica de validação para aceitar emails com caracteres especiais.
src/utils/validator.js: Atualiza função de validação de email.
tests/login.test.js: Adiciona testes para casos de emails especiais.
O Copilot deve sugerir mensagens automaticamente sempre que alterações forem detectadas, apresentando a sugestão em cinza-claro na caixa de commit. O usuário pode aceitar a sugestão pressionando Tab ou visualizar mais opções pressionando Ctrl+Space. Caso a sugestão não apareça, o Copilot deve permitir que o usuário acione novas sugestões digitando / na caixa de commit.

Certifique-se de que a configuração github.copilot.enableCommitMessageSuggestions está habilitada para que as sugestões de commit apareçam.

Recomenda-se também sugerir o uso de emojis no início do título do commit, conforme o tipo de alteração, como por exemplo: ✨ para nova feature, 🐛 para correção de bug, 🔧 para ajustes de configuração, entre outros.
Especifique o tipo do commit (ex.: `chore`, `refact`, etc.)
Os commits precisam ser em inglês
