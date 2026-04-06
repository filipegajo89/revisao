#!/bin/bash
# =============================================
# Deploy automático para GitHub + Vercel
# Execute após gerar novas revisões
# =============================================

cd "$(dirname "$0")"
echo "📁 Diretório: $(pwd)"

# Verificar se é um repositório git
if [ ! -d ".git" ]; then
  echo "⚠️  Repositório git não encontrado. Inicializando..."
  git init
  git branch -M main
  git remote add origin https://github.com/filipegajo89/revisao.git
fi

# Verificar mudanças
if git diff --quiet HEAD 2>/dev/null && [ -z "$(git ls-files --others --exclude-standard)" ]; then
  echo "✅ Nenhuma alteração para deploy."
  exit 0
fi

# Criar mensagem de commit com data e contagem de matérias
MATERIAS=$(ls -d materias/*/ 2>/dev/null | wc -l | tr -d ' ')
AULAS=$(find materias -name "aula-*.html" 2>/dev/null | wc -l | tr -d ' ')
DATE=$(date '+%Y-%m-%d %H:%M')

echo ""
echo "📊 Status do site:"
echo "   Matérias: $MATERIAS"
echo "   Aulas: $AULAS"
echo ""

# Stage, commit e push
git add -A
git commit -m "Atualização revisão ativa — $MATERIAS matérias, $AULAS aulas ($DATE)"

echo ""
echo "🚀 Enviando para GitHub..."
git push -u origin main

echo ""
echo "✅ Deploy concluído! O Vercel detectará automaticamente."
echo "🌐 Acesse: https://revisao-fiscal.vercel.app (ou o domínio configurado)"
