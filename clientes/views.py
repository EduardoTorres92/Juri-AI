import json

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.messages import constants
from django.contrib import messages
from django.urls import reverse
from django.utils.dateparse import parse_datetime

from .models import Cliente, Documentos, Honorario, Prazo, Processo


@login_required
def dashboard(request):
    user = request.user
    clientes_qs = Cliente.objects.filter(user=user)

    # Faturamento
    from django.utils import timezone
    hoje = timezone.now().date()
    honorarios = Honorario.objects.filter(user=user)
    faturamento_total = honorarios.aggregate(s=Sum('valor'))['s'] or 0
    faturamento_pago = honorarios.filter(status='pago').aggregate(s=Sum('valor'))['s'] or 0
    faturamento_pendente = honorarios.filter(status='pendente').aggregate(s=Sum('valor'))['s'] or 0
    valor_a_receber = faturamento_pendente
    pct_recebida = (float(faturamento_pago) / float(faturamento_total) * 100) if faturamento_total else 0
    boletos_atraso = honorarios.filter(status='pendente', data_vencimento__lt=hoje).exclude(data_vencimento__isnull=True)
    qtd_boletos_atraso = boletos_atraso.count()
    valor_boletos_atraso = boletos_atraso.aggregate(s=Sum('valor'))['s'] or 0

    # Faturamento por mês (últimos 6 meses)
    from datetime import timedelta
    seis_meses_atras = timezone.now().date() - timedelta(days=180)
    faturamento_por_mes = list(
        honorarios.filter(status='pago', data__gte=seis_meses_atras)
        .annotate(mes=TruncMonth('data'))
        .values('mes')
        .annotate(total=Sum('valor'))
        .order_by('mes')
    )

    # Clientes
    total_clientes = clientes_qs.count()
    clientes_ativos = clientes_qs.filter(status=True).count()
    clientes_pf = clientes_qs.filter(tipo='PF').count()
    clientes_pj = clientes_qs.filter(tipo='PJ').count()

    # Casos = Processos (protocolos). Documentos = anexos (PDFs, prints) por cliente.
    processos_qs = Processo.objects.filter(cliente__user=user)
    total_casos = processos_qs.count()

    documentos_qs = Documentos.objects.filter(cliente__user=user)
    total_documentos = documentos_qs.count()
    docs_por_tipo = list(
        documentos_qs.values('tipo').annotate(total=Count('id')).order_by('tipo')
    )
    tipo_labels = dict(Documentos.TIPO_CHOICES)

    # Análises (documentos analisados)
    from ia.models import AnaliseJurisprudencia
    analises_qs = AnaliseJurisprudencia.objects.filter(documento__cliente__user=user)
    total_analises = analises_qs.count()
    analises_por_classificacao = list(
        analises_qs.values('classificacao').annotate(total=Count('id')).order_by('classificacao')
    )

    # Perguntas/consultas
    from ia.models import Pergunta
    total_perguntas = Pergunta.objects.filter(cliente__user=user).count()

    # Documentos sem análise (pendentes)
    docs_com_analise = set(analises_qs.values_list('documento_id', flat=True))
    docs_sem_analise = documentos_qs.exclude(id__in=docs_com_analise).count()

    # Consultas/documentos por mês (últimos 6 meses)
    from django.db.models.functions import TruncMonth as TM
    seis_meses_atras_dt = timezone.now() - timedelta(days=180)
    docs_por_mes = list(
        documentos_qs.filter(data_upload__gte=seis_meses_atras_dt)
        .annotate(mes=TM('data_upload'))
        .values('mes')
        .annotate(total=Count('id'))
        .order_by('mes')
    )
    analises_por_mes = list(
        analises_qs.filter(data_criacao__gte=seis_meses_atras_dt)
        .annotate(mes=TM('data_criacao'))
        .values('mes')
        .annotate(total=Count('id'))
        .order_by('mes')
    )

    # Casos recentes = Processos (protocolos), ordenados por mais recente
    casos_recentes = list(processos_qs.select_related('cliente').order_by('-id')[:8])
    cliente_ids = [p.cliente_id for p in casos_recentes]
    # Documentos por cliente (contagem e última interação)
    from django.db.models import Max
    docs_stats_qs = Documentos.objects.filter(cliente_id__in=cliente_ids).values('cliente_id').annotate(
        total=Count('id'), ultima=Max('data_upload')
    )
    docs_count = {r['cliente_id']: r['total'] for r in docs_stats_qs}
    docs_ultima = {r['cliente_id']: r['ultima'] for r in docs_stats_qs}
    clientes_com_analise = set(
        Documentos.objects.filter(id__in=docs_com_analise, cliente_id__in=cliente_ids)
        .values_list('cliente_id', flat=True)
    )
    # Montar lista de casos com dados para o template
    casos_recentes_com_dados = [
        {
            'caso': p,
            'qtd_docs': docs_count.get(p.cliente_id, 0),
            'ultima': docs_ultima.get(p.cliente_id),
            'tem_analise': p.cliente_id in clientes_com_analise,
        }
        for p in casos_recentes
    ]

    # Prazos para o calendário
    prazos_qs = Prazo.objects.filter(user=user).select_related('cliente', 'processo')

    # Clientes e processos para o modal de novo prazo no dashboard
    clientes_list = list(clientes_qs.order_by('nome'))
    processos_list = list(Processo.objects.filter(cliente__user=user).select_related('cliente').order_by('cliente__nome', 'id'))
    # Agrupar processos por cliente
    from collections import defaultdict
    proc_map = defaultdict(list)
    for p in processos_list:
        proc_map[str(p.cliente_id)].append({'id': p.id, 'label': p.numero_processo or p.descricao or 'Processo'})
    processos_por_cliente = json.dumps(dict(proc_map))

    # Serializar para JSON no template
    faturamento_por_mes_json = json.dumps([
        {'mes': f['mes'].isoformat() if f['mes'] else '', 'total': str(f['total'])}
        for f in faturamento_por_mes
    ])
    docs_por_mes_json = json.dumps([
        {'mes': d['mes'].isoformat() if d['mes'] else '', 'total': d['total']}
        for d in docs_por_mes
    ])
    analises_por_mes_json = json.dumps([
        {'mes': a['mes'].isoformat() if a['mes'] else '', 'total': a['total']}
        for a in analises_por_mes
    ])

    return render(request, 'dashboard.html', {
        'prazos': prazos_qs,
        'faturamento_total': faturamento_total,
        'faturamento_pago': faturamento_pago,
        'faturamento_pendente': faturamento_pendente,
        'valor_a_receber': valor_a_receber,
        'pct_recebida': pct_recebida,
        'qtd_boletos_atraso': qtd_boletos_atraso,
        'valor_boletos_atraso': valor_boletos_atraso,
        'faturamento_por_mes': faturamento_por_mes,
        'faturamento_por_mes_json': faturamento_por_mes_json,
        'total_clientes': total_clientes,
        'clientes_ativos': clientes_ativos,
        'clientes_pf': clientes_pf,
        'clientes_pj': clientes_pj,
        'total_casos': total_casos,
        'total_documentos': total_documentos,
        'docs_por_tipo': json.dumps(list(docs_por_tipo)),
        'tipo_labels': json.dumps(tipo_labels),
        'total_analises': total_analises,
        'analises_por_classificacao': json.dumps(list(analises_por_classificacao)),
        'total_perguntas': total_perguntas,
        'docs_sem_analise': docs_sem_analise,
        'docs_por_mes_json': docs_por_mes_json,
        'analises_por_mes_json': analises_por_mes_json,
        'casos_recentes_com_dados': casos_recentes_com_dados,
        'docs_com_analise': list(docs_com_analise),
        'clientes_list': clientes_list,
        'processos_por_cliente': processos_por_cliente,
    })


@login_required
def clientes(request):
    if request.method == 'GET':
        from django.db.models import Q
        from django.core.paginator import Paginator

        qs = Cliente.objects.filter(user=request.user).order_by('nome')

        # Busca
        busca = (request.GET.get('q') or '').strip()
        if busca:
            qs = qs.filter(
                Q(nome__icontains=busca) |
                Q(email__icontains=busca) |
                Q(cpf_cnpj__icontains=busca.replace('.', '').replace('-', '').replace('/', ''))
            )

        # Filtro status
        status_filtro = request.GET.get('status', '')
        if status_filtro == 'ativo':
            qs = qs.filter(status=True, vip=False)
        elif status_filtro == 'vip':
            qs = qs.filter(vip=True)
        elif status_filtro == 'inativo':
            qs = qs.filter(status=False)

        # Filtro tipo
        tipo_filtro = request.GET.get('tipo', '')
        if tipo_filtro in ('PF', 'PJ'):
            qs = qs.filter(tipo=tipo_filtro)

        total = qs.count()
        ativos = Cliente.objects.filter(user=request.user, status=True, vip=False).count()
        vip_count = Cliente.objects.filter(user=request.user, vip=True).count()
        inativos = Cliente.objects.filter(user=request.user, status=False).count()

        # Paginação
        per_page = 10
        paginator = Paginator(qs, per_page)
        page_num = request.GET.get('page', 1)
        page = paginator.get_page(page_num)
        clientes_list = list(page.object_list)

        # Montar último caso para cada cliente
        processo_por_cliente = {}
        for p in Processo.objects.filter(cliente__in=clientes_list).order_by('cliente', '-id'):
            if p.cliente_id not in processo_por_cliente:
                processo_por_cliente[p.cliente_id] = ('processo', p.descricao or p.numero_processo or f'Processo R$ {p.valor_total}', p.id)
        doc_por_cliente = {}
        for d in Documentos.objects.filter(cliente__in=clientes_list).order_by('cliente', '-data_upload'):
            if d.cliente_id not in doc_por_cliente:
                doc_por_cliente[d.cliente_id] = (d.nome_exibicao, d.data_upload)

        # qtd documentos por cliente
        docs_por_cliente_ct = dict(
            Documentos.objects.filter(cliente__in=clientes_list).values('cliente_id').annotate(ct=Count('id')).values_list('cliente_id', 'ct')
        )
        clientes_com_ultimo = []
        for c in clientes_list:
            proc = processo_por_cliente.get(c.id)
            doc = doc_por_cliente.get(c.id)
            # Caso = protocolo (Processo). Priorizar processo como "último caso"
            if proc:
                ultimo_desc, ultimo_data = proc[1], None
            elif doc:
                ultimo_desc, ultimo_data = doc[0], doc[1]
            else:
                ultimo_desc, ultimo_data = None, None
            qtd_docs = docs_por_cliente_ct.get(c.id, 0)
            clientes_com_ultimo.append({
                'cliente': c,
                'ultimo_desc': ultimo_desc,
                'ultimo_data': ultimo_data,
                'qtd_documentos': qtd_docs,
            })

        return render(request, 'clientes.html', {
            'clientes_com_ultimo': clientes_com_ultimo,
            'page': page,
            'paginator': paginator,
            'total': total,
            'ativos': ativos,
            'vip_count': vip_count,
            'inativos': inativos,
            'busca': busca,
            'status_filtro': status_filtro,
            'tipo_filtro': tipo_filtro,
        })
    elif request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        email = request.POST.get('email', '').strip()
        cpf_cnpj = (request.POST.get('cpf_cnpj') or '').strip().replace('.', '').replace('-', '').replace('/', '')
        telefone = (request.POST.get('telefone') or '').strip()
        tipo = request.POST.get('tipo', 'PF')
        status = request.POST.get('status') == 'on'
        vip = request.POST.get('vip') == 'on'

        Cliente.objects.create(
            nome=nome,
            email=email,
            cpf_cnpj=cpf_cnpj,
            telefone=telefone,
            tipo=tipo,
            status=status,
            vip=vip,
            user=request.user
        )

        messages.add_message(request, constants.SUCCESS, 'Cliente cadastrado com sucesso!')
        return redirect('clientes')


@login_required
def cliente_editar(request, id):
    cliente_obj = get_object_or_404(Cliente, id=id, user=request.user)
    if request.method == 'GET':
        return render(request, 'cliente_editar.html', {'cliente': cliente_obj})
    elif request.method == 'POST':
        cliente_obj.nome = request.POST.get('nome', '').strip()
        cliente_obj.email = request.POST.get('email', '').strip()
        cliente_obj.cpf_cnpj = (request.POST.get('cpf_cnpj') or '').strip().replace('.', '').replace('-', '').replace('/', '')
        cliente_obj.telefone = (request.POST.get('telefone') or '').strip()
        cliente_obj.tipo = request.POST.get('tipo', 'PF')
        cliente_obj.status = request.POST.get('status') == 'on'
        cliente_obj.vip = request.POST.get('vip') == 'on'
        cliente_obj.save()
        messages.add_message(request, constants.SUCCESS, 'Cliente atualizado com sucesso!')
        return redirect('cliente', id=cliente_obj.id)


@login_required
def cliente(request, id):
    cliente_obj = get_object_or_404(Cliente, id=id, user=request.user)
    if request.method == 'GET':
        documentos = Documentos.objects.filter(cliente=cliente_obj)
        processos = Processo.objects.filter(cliente=cliente_obj)
        honorarios = Honorario.objects.filter(cliente=cliente_obj).select_related('processo')
        prazos = Prazo.objects.filter(cliente=cliente_obj).select_related('processo').order_by('data')
        documento_processando = request.GET.get('documento_processando')
        return render(request, 'cliente.html', {
            'cliente': cliente_obj,
            'documentos': documentos,
            'processos': processos,
            'honorarios': honorarios,
            'prazos': prazos,
            'documento_processando': documento_processando,
        })
    elif request.method == 'POST':
        tipo = request.POST.get('tipo')
        documento = request.FILES.get('documento')
        data = request.POST.get('data')

        doc = Documentos(cliente=cliente_obj, tipo=tipo, arquivo=documento)
        if data:
            data_upload = parse_datetime(data)
            if data_upload:
                doc.data_upload = data_upload
        doc.save()

        messages.add_message(
            request, constants.SUCCESS,
            'Documento enviado com sucesso! O processamento (OCR e indexação) está em andamento em segundo plano.'
        )
        url = reverse('cliente', kwargs={'id': cliente_obj.id})
        return redirect(f'{url}?documento_processando={doc.id}')


@login_required
def documento_excluir(request, id):
    documento = get_object_or_404(Documentos, id=id)
    if documento.cliente.user_id != request.user.id:
        messages.add_message(request, constants.ERROR, 'Acesso negado.')
        return redirect('clientes')
    cliente_id = documento.cliente_id
    documento.arquivo.delete(save=False)
    documento.delete()
    messages.add_message(request, constants.SUCCESS, 'Documento excluído com sucesso.')
    return redirect('cliente', id=cliente_id)


@login_required
def documento_renomear(request, id):
    documento = get_object_or_404(Documentos, id=id)
    if documento.cliente.user_id != request.user.id:
        messages.add_message(request, constants.ERROR, 'Acesso negado.')
        return redirect('clientes')
    if request.method == 'POST':
        nome = (request.POST.get('nome') or '').strip()
        if nome:
            documento.nome = nome
            documento.save()
            messages.add_message(request, constants.SUCCESS, 'Documento renomeado com sucesso.')
        return redirect('cliente', id=documento.cliente_id)
    return redirect('cliente', id=documento.cliente_id)


@login_required
def processo_criar(request, cliente_id):
    cliente_obj = get_object_or_404(Cliente, id=cliente_id, user=request.user)
    if request.method == 'POST':
        numero = (request.POST.get('numero_processo') or '').strip()
        descricao = (request.POST.get('descricao') or '').strip()
        valor = request.POST.get('valor_total') or '0'
        try:
            from decimal import Decimal
            valor_decimal = Decimal(valor.replace(',', '.'))
        except Exception:
            valor_decimal = Decimal('0')
        Processo.objects.create(
            cliente=cliente_obj,
            numero_processo=numero,
            descricao=descricao,
            valor_total=valor_decimal,
            user=request.user,
        )
        messages.add_message(request, constants.SUCCESS, 'Processo cadastrado com sucesso!')
    return redirect('cliente', id=cliente_id)


@login_required
def processo_editar(request, id):
    processo = get_object_or_404(Processo, id=id, user=request.user)
    if request.method == 'POST':
        processo.numero_processo = (request.POST.get('numero_processo') or '').strip()
        processo.descricao = (request.POST.get('descricao') or '').strip()
        valor = request.POST.get('valor_total') or '0'
        try:
            from decimal import Decimal
            processo.valor_total = Decimal(valor.replace(',', '.'))
        except Exception:
            pass
        processo.save()
        messages.add_message(request, constants.SUCCESS, 'Processo atualizado com sucesso!')
    return redirect('cliente', id=processo.cliente_id)


@login_required
def processo_excluir(request, id):
    processo = get_object_or_404(Processo, id=id, user=request.user)
    cliente_id = processo.cliente_id
    processo.delete()
    messages.add_message(request, constants.SUCCESS, 'Processo excluído com sucesso.')
    return redirect('cliente', id=cliente_id)


@login_required
def honorario_criar(request, cliente_id):
    cliente_obj = get_object_or_404(Cliente, id=cliente_id, user=request.user)
    if request.method == 'POST':
        valor = request.POST.get('valor') or '0'
        descricao = (request.POST.get('descricao') or '').strip()
        data_str = request.POST.get('data')
        data_venc_str = request.POST.get('data_vencimento') or None
        processo_id = request.POST.get('processo') or None
        status = request.POST.get('status', 'pendente')
        try:
            from decimal import Decimal
            from datetime import datetime
            valor_decimal = Decimal(valor.replace(',', '.'))
            data = datetime.strptime(data_str, '%Y-%m-%d').date() if data_str else None
            data_venc = datetime.strptime(data_venc_str, '%Y-%m-%d').date() if data_venc_str else None
        except Exception:
            messages.add_message(request, constants.ERROR, 'Dados inválidos.')
            return redirect('cliente', id=cliente_id)
        if not data:
            messages.add_message(request, constants.ERROR, 'Data é obrigatória.')
            return redirect('cliente', id=cliente_id)
        proc = Processo.objects.filter(id=processo_id, cliente=cliente_obj).first() if processo_id else None
        Honorario.objects.create(
            cliente=cliente_obj,
            processo=proc,
            valor=valor_decimal,
            descricao=descricao,
            data=data,
            data_vencimento=data_venc,
            status=status,
            user=request.user,
        )
        messages.add_message(request, constants.SUCCESS, 'Honorário cadastrado com sucesso!')
    return redirect('cliente', id=cliente_id)


@login_required
def honorario_editar(request, id):
    honorario = get_object_or_404(Honorario, id=id, user=request.user)
    if request.method == 'POST':
        valor = request.POST.get('valor') or '0'
        honorario.descricao = (request.POST.get('descricao') or '').strip()
        data_str = request.POST.get('data')
        data_venc_str = request.POST.get('data_vencimento') or None
        processo_id = request.POST.get('processo') or None
        honorario.status = request.POST.get('status', 'pendente')
        try:
            from decimal import Decimal
            from datetime import datetime
            honorario.valor = Decimal(valor.replace(',', '.'))
            if data_str:
                honorario.data = datetime.strptime(data_str, '%Y-%m-%d').date()
            honorario.data_vencimento = datetime.strptime(data_venc_str, '%Y-%m-%d').date() if (data_venc_str and data_venc_str.strip()) else None
        except Exception:
            pass
        honorario.processo = Processo.objects.filter(id=processo_id, cliente=honorario.cliente).first() if processo_id else None
        honorario.save()
        messages.add_message(request, constants.SUCCESS, 'Honorário atualizado com sucesso!')
    return redirect('cliente', id=honorario.cliente_id)


@login_required
def honorario_excluir(request, id):
    honorario = get_object_or_404(Honorario, id=id, user=request.user)
    cliente_id = honorario.cliente_id
    honorario.delete()
    messages.add_message(request, constants.SUCCESS, 'Honorário excluído com sucesso.')
    return redirect('cliente', id=cliente_id)


@login_required
def prazo_criar(request, cliente_id):
    cliente_obj = get_object_or_404(Cliente, id=cliente_id, user=request.user)
    if request.method == 'POST':
        data_str = request.POST.get('data')
        descricao = (request.POST.get('descricao') or '').strip()
        processo_id = request.POST.get('processo') or None
        if not data_str or not descricao:
            messages.add_message(request, constants.ERROR, 'Data e descrição são obrigatórios.')
            return redirect('cliente', id=cliente_id)
        try:
            from datetime import datetime
            data = datetime.strptime(data_str, '%Y-%m-%d').date()
        except Exception:
            messages.add_message(request, constants.ERROR, 'Data inválida.')
            return redirect('cliente', id=cliente_id)
        proc = Processo.objects.filter(id=processo_id, cliente=cliente_obj).first() if processo_id else None
        Prazo.objects.create(
            cliente=cliente_obj,
            processo=proc,
            data=data,
            descricao=descricao,
            user=request.user,
        )
        messages.add_message(request, constants.SUCCESS, 'Prazo cadastrado com sucesso!')
    return redirect('cliente', id=cliente_id)


@login_required
def prazo_criar_geral(request):
    """Cria prazo a partir do dashboard (seleciona cliente)."""
    if request.method == 'POST':
        cliente_id = request.POST.get('cliente')
        data_str = request.POST.get('data')
        descricao = (request.POST.get('descricao') or '').strip()
        processo_id = request.POST.get('processo') or None
        if not cliente_id or not data_str or not descricao:
            messages.add_message(request, constants.ERROR, 'Cliente, data e descrição são obrigatórios.')
            return redirect('dashboard')
        cliente_obj = get_object_or_404(Cliente, id=cliente_id, user=request.user)
        try:
            from datetime import datetime
            data = datetime.strptime(data_str, '%Y-%m-%d').date()
        except Exception:
            messages.add_message(request, constants.ERROR, 'Data inválida.')
            return redirect('dashboard')
        proc = Processo.objects.filter(id=processo_id, cliente=cliente_obj).first() if processo_id else None
        Prazo.objects.create(
            cliente=cliente_obj,
            processo=proc,
            data=data,
            descricao=descricao,
            user=request.user,
        )
        messages.add_message(request, constants.SUCCESS, 'Prazo cadastrado com sucesso!')
    return redirect('dashboard')


@login_required
def prazo_editar(request, id):
    prazo = get_object_or_404(Prazo, id=id, user=request.user)
    if request.method == 'POST':
        data_str = request.POST.get('data')
        prazo.descricao = (request.POST.get('descricao') or '').strip()
        processo_id = request.POST.get('processo') or None
        try:
            from datetime import datetime
            if data_str:
                prazo.data = datetime.strptime(data_str, '%Y-%m-%d').date()
        except Exception:
            pass
        prazo.processo = Processo.objects.filter(id=processo_id, cliente=prazo.cliente).first() if processo_id else None
        prazo.save()
        messages.add_message(request, constants.SUCCESS, 'Prazo atualizado com sucesso!')
    return redirect('cliente', id=prazo.cliente_id)


@login_required
def prazo_excluir(request, id):
    prazo = get_object_or_404(Prazo, id=id, user=request.user)
    cliente_id = prazo.cliente_id
    prazo.delete()
    messages.add_message(request, constants.SUCCESS, 'Prazo excluído com sucesso.')
    return redirect('cliente', id=cliente_id)


@login_required
def prazos_api(request):
    """Retorna prazos em JSON para o calendário (FullCalendar)."""
    from django.http import JsonResponse
    prazos = Prazo.objects.filter(user=request.user).select_related('cliente', 'processo')
    events = []
    for p in prazos:
        title = f"{p.descricao} - {p.cliente.nome}"
        if p.processo:
            title += f" ({p.processo.numero_processo or p.processo.descricao or 'Processo'})"
        events.append({
            'id': p.id,
            'title': title,
            'start': p.data.isoformat(),
            'allDay': True,
            'url': reverse('cliente', args=[p.cliente_id]),
            'backgroundColor': '#ef4444' if p.em_atraso else '#8b5cf6',
        })
    return JsonResponse(events, safe=False)
