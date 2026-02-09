"""
Serviço de integração com a API Asaas para cobranças via boleto.
"""
import logging
from datetime import date
from decimal import Decimal
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class AsaasError(Exception):
    """Erro na comunicação com a API Asaas."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class AsaasService:
    """Cliente para a API Asaas."""

    def __init__(self):
        self.api_key = getattr(settings, 'ASAAS_API_KEY', None) or ''
        self.base_url = getattr(settings, 'ASAAS_BASE_URL', 'https://api.asaas.com').rstrip('/')
        self.headers = {
            'Content-Type': 'application/json',
            'access_token': self.api_key,
            'User-Agent': 'JuriAI/1.0',
        }

    def _request(self, method: str, path: str, json_data: Optional[dict] = None) -> dict:
        """Executa requisição à API Asaas."""
        if not self.api_key:
            raise AsaasError('ASAAS_API_KEY não configurada no .env')

        url = f'{self.base_url}{path}'
        try:
            resp = requests.request(
                method,
                url,
                headers=self.headers,
                json=json_data,
                timeout=30,
            )
            data = resp.json() if resp.content else {}
        except requests.RequestException as e:
            logger.exception('Erro ao chamar API Asaas: %s', e)
            raise AsaasError(f'Erro de conexão: {e}')

        if resp.status_code >= 400:
            errors = data.get('errors', [])
            msg = '; '.join(e.get('description', str(e)) for e in errors) if errors else resp.text
            logger.warning('Asaas API error %s: %s', resp.status_code, msg)
            raise AsaasError(msg or f'Erro {resp.status_code}', resp.status_code, data)

        return data

    def get_or_create_customer(self, cliente) -> str:
        """
        Retorna o asaas_customer_id do cliente. Cria no Asaas se não existir.
        Exige CPF/CNPJ e telefone.
        """
        if cliente.asaas_customer_id:
            return cliente.asaas_customer_id

        cpf_cnpj = (cliente.cpf_cnpj or '').replace('.', '').replace('-', '').replace('/', '').strip()
        if not cpf_cnpj or len(cpf_cnpj) < 11:
            raise AsaasError('Cliente precisa ter CPF ou CNPJ cadastrado para gerar boleto.')

        telefone = (cliente.telefone or '').replace('(', '').replace(')', '').replace('-', '').replace(' ', '').strip()
        if not telefone or len(telefone) < 10:
            raise AsaasError('Cliente precisa ter telefone cadastrado para gerar boleto.')

        payload = {
            'name': cliente.nome or 'Cliente',
            'cpfCnpj': cpf_cnpj,
            'email': cliente.email or '',
            'mobilePhone': telefone,
        }

        data = self._request('POST', '/v3/customers', json_data=payload)
        customer_id = data.get('id')
        if not customer_id:
            raise AsaasError('Resposta da API Asaas sem ID do cliente')

        cliente.asaas_customer_id = customer_id
        cliente.save(update_fields=['asaas_customer_id'])
        return customer_id

    def criar_cobranca_boleto(self, cliente, honorario) -> dict:
        """
        Cria cobrança por boleto no Asaas.
        Retorna dict com id, bankSlipUrl, status.
        """
        customer_id = self.get_or_create_customer(cliente)

        due_date = honorario.data_vencimento or honorario.data
        if isinstance(due_date, date):
            due_date = due_date.strftime('%Y-%m-%d')

        value = float(honorario.valor)
        description = honorario.descricao or f'Honorário - {honorario.cliente.nome}'

        payload = {
            'customer': customer_id,
            'billingType': 'BOLETO',
            'value': value,
            'dueDate': due_date,
            'description': description[:300],
        }

        data = self._request('POST', '/v3/lean/payments', json_data=payload)
        return {
            'id': data.get('id'),
            'bankSlipUrl': data.get('bankSlipUrl', ''),
            'status': data.get('status', 'PENDING'),
        }

    def obter_boleto_pdf(self, payment_id: str) -> Optional[str]:
        """Retorna URL do PDF do boleto."""
        data = self._request('GET', f'/v3/lean/payments/{payment_id}')
        return data.get('bankSlipUrl')

    def consultar_status(self, payment_id: str) -> str:
        """Retorna status da cobrança (PENDING, RECEIVED, etc.)."""
        data = self._request('GET', f'/v3/lean/payments/{payment_id}')
        return data.get('status', 'UNKNOWN')
