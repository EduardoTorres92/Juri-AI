import time
from typing import Iterator

from agno.agent import RunOutputEvent, RunEvent
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.messages import constants
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from areas.models import AreaAtuacao

from clientes.models import Cliente, Documentos

from .agents import JuriAI
from .agente_langchain import JurisprudenciaAI
from .models import Pergunta, PerguntaArea, ContextRag, ContextRagArea, AnaliseJurisprudencia


@csrf_exempt
def chat(request, id):
    cliente = Cliente.objects.get(id=id)
    if request.method == 'GET':
        historico = Pergunta.objects.filter(cliente=cliente).order_by('-id')[:15]
        return render(request, 'chat.html', {'cliente': cliente, 'historico': historico})
    elif request.method == 'POST':
        pergunta = request.POST.get('pergunta')
        pergunta_model = Pergunta(pergunta=pergunta, cliente=cliente)
        pergunta_model.save()
        return JsonResponse({'id': pergunta_model.id})


@csrf_exempt
def stream_resposta(request):
    id_pergunta = request.POST.get('id_pergunta')
    pergunta = get_object_or_404(Pergunta, id=id_pergunta)

    def gerar_resposta():
        agent = JuriAI.build_agent(knowledge_filters={'cliente_id': pergunta.cliente.id})
        stream: Iterator[RunOutputEvent] = agent.run(pergunta.pergunta, stream=True, stream_events=True)
        for chunk in stream:
            if chunk.event == RunEvent.tool_call_completed:
                context = ContextRag(
                    content=chunk.tool.result,
                    tool_name=chunk.tool.tool_name,
                    tool_args=chunk.tool.tool_args,
                    pergunta=pergunta,
                )
                context.save()
            if chunk.event == RunEvent.run_content:
                yield str(chunk.content)

    response = StreamingHttpResponse(
        gerar_resposta(),
        content_type='text/plain; charset=utf-8'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'

    return response


@login_required
def chat_area(request, id):
    area = get_object_or_404(AreaAtuacao, id=id, user=request.user)
    if request.method == 'GET':
        historico = PerguntaArea.objects.filter(area=area).order_by('-id')[:15]
        return render(request, 'ia/chat_area.html', {'area': area, 'historico': historico})
    elif request.method == 'POST':
        pergunta = request.POST.get('pergunta')
        pergunta_model = PerguntaArea(pergunta=pergunta, area=area)
        pergunta_model.save()
        return JsonResponse({'id': pergunta_model.id})


@login_required
@csrf_exempt
def stream_resposta_area(request):
    id_pergunta = request.POST.get('id_pergunta')
    pergunta = get_object_or_404(PerguntaArea, id=id_pergunta)
    if pergunta.area.user_id != request.user.id:
        return JsonResponse({'error': 'Acesso negado'}, status=403)

    def gerar_resposta():
        agent = JuriAI.build_agent_area(knowledge_filters={'area_id': pergunta.area.id})
        stream: Iterator[RunOutputEvent] = agent.run(pergunta.pergunta, stream=True, stream_events=True)
        for chunk in stream:
            if chunk.event == RunEvent.tool_call_completed and hasattr(chunk, 'tool') and chunk.tool:
                try:
                    context = ContextRagArea(
                        content=chunk.tool.result,
                        tool_name=getattr(chunk.tool, 'tool_name', 'knowledge'),
                        tool_args=getattr(chunk.tool, 'tool_args', None),
                        pergunta=pergunta,
                    )
                    context.save()
                except Exception:
                    pass
            if chunk.event == RunEvent.run_content:
                yield str(chunk.content)

    response = StreamingHttpResponse(
        gerar_resposta(),
        content_type='text/plain; charset=utf-8'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


def ver_referencias(request, id):
    pergunta = get_object_or_404(Pergunta, id=id)
    contextos = ContextRag.objects.filter(pergunta=pergunta)
    return render(request, 'ver_referencias.html', {
        'pergunta': pergunta,
        'contextos': contextos,
    })


def ver_conversa(request, id):
    """Exibe a conversa completa (pergunta + resposta) em nova janela."""
    pergunta = get_object_or_404(Pergunta, id=id)
    return render(request, 'ia/ver_conversa.html', {
        'pergunta': pergunta,
        'tipo': 'cliente',
        'ver_referencias_url': 'ver_referencias',
        'voltar_url': 'cliente',
        'voltar_id': pergunta.cliente_id,
    })


@login_required
def ver_conversa_area(request, id):
    """Exibe a conversa completa (pergunta + resposta) da área em nova janela."""
    pergunta = get_object_or_404(PerguntaArea, id=id)
    if pergunta.area.user_id != request.user.id:
        return redirect('areas_list')
    return render(request, 'ia/ver_conversa.html', {
        'pergunta': pergunta,
        'tipo': 'area',
        'ver_referencias_url': 'ver_referencias_area',
        'voltar_url': 'area_detail',
        'voltar_id': pergunta.area_id,
    })


@login_required
def ver_referencias_area(request, id):
    pergunta = get_object_or_404(PerguntaArea, id=id)
    if pergunta.area.user_id != request.user.id:
        return redirect('areas_list')
    contextos = ContextRagArea.objects.filter(pergunta=pergunta)
    return render(request, 'ia/ver_referencias_area.html', {
        'pergunta': pergunta,
        'contextos': contextos,
    })


def analise_jurisprudencia(request, id):
    documento = get_object_or_404(Documentos, id=id)
    analise = AnaliseJurisprudencia.objects.filter(documento=documento).first()
    return render(request, 'analise_jurisprudencia.html', {
        'documento': documento,
        'analise': analise,
    })


@login_required
def salvar_resposta(request):
    """Salva a resposta no modelo após o streaming (chamado pelo JS)."""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'erro': 'Método não permitido'}, status=405)
    pergunta_id = request.POST.get('pergunta_id')
    resposta = request.POST.get('resposta', '')
    tipo = request.POST.get('tipo', 'cliente')  # 'cliente' ou 'area'
    if not pergunta_id:
        return JsonResponse({'ok': False, 'erro': 'pergunta_id obrigatório'}, status=400)
    try:
        if tipo == 'area':
            pergunta = get_object_or_404(PerguntaArea, id=pergunta_id)
            if pergunta.area.user_id != request.user.id:
                return JsonResponse({'ok': False, 'erro': 'Acesso negado'}, status=403)
        else:
            pergunta = get_object_or_404(Pergunta, id=pergunta_id)
            if pergunta.cliente.user_id != request.user.id:
                return JsonResponse({'ok': False, 'erro': 'Acesso negado'}, status=403)
        pergunta.resposta = resposta or ''
        pergunta.save(update_fields=['resposta'])
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'erro': str(e)}, status=500)


@login_required
def documento_status(request, id):
    """Retorna se o documento já foi processado (OCR concluído)."""
    documento = get_object_or_404(Documentos, id=id)
    if documento.cliente.user_id != request.user.id:
        return JsonResponse({'processado': False, 'erro': 'Acesso negado'}, status=403)
    processado = bool(documento.content and str(documento.content).strip())
    return JsonResponse({'processado': processado})


def processar_analise(request, id):
    if request.method != 'POST':
        messages.add_message(request, constants.ERROR, 'Método não permitido.')
        return redirect('analise_jurisprudencia', id=id)

    try:
        documento = get_object_or_404(Documentos, id=id)
        start_time = time.time()

        agent = JurisprudenciaAI()
        response = agent.run(documento.content or '')

        processing_time = int(time.time() - start_time)

        indice = response.indice_risco
        if indice <= 30:
            classificacao = "Baixo"
        elif indice <= 60:
            classificacao = "Médio"
        elif indice <= 80:
            classificacao = "Alto"
        else:
            classificacao = "Crítico"

        analise, created = AnaliseJurisprudencia.objects.update_or_create(
            documento=documento,
            defaults={
                'indice_risco': indice,
                'classificacao': classificacao,
                'erros_coerencia': response.erros_coerencia,
                'riscos_juridicos': response.riscos_juridicos,
                'problemas_formatacao': response.problemas_formatacao,
                'red_flags': response.red_flags,
                'tempo_processamento': processing_time,
            }
        )

        if created:
            messages.add_message(request, constants.SUCCESS, 'Análise realizada e salva com sucesso!')
        else:
            messages.add_message(request, constants.SUCCESS, 'Análise atualizada com sucesso!')

        return redirect('analise_jurisprudencia', id=id)
    except Exception as e:
        messages.add_message(request, constants.ERROR, f'Erro ao processar análise: {str(e)}')
        return redirect('analise_jurisprudencia', id=id)
