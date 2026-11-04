"""Caso de uso: salvar/atualizar os interesses, o orçamento e a localização do usuário."""
from backend.models.interesse import Interesse
from backend.models.preferencia import Preferencia
from backend.utils.erros import ErroDeValidacao
from backend.utils.validadores import validar_orcamento


class SalvarPreferenciasService:
    def executar(self, usuario, dados):
        slugs = dados.get("interesses") or []
        if not isinstance(slugs, list) or not slugs:
            raise ErroDeValidacao("Escolha pelo menos um interesse.", campo="interesses")

        interesses = Interesse.buscar_por_slugs(slugs)
        if not interesses:
            raise ErroDeValidacao("Interesses inválidos.", campo="interesses")

        orcamento = validar_orcamento(dados.get("orcamento", 2))
        cidade = (dados.get("cidade") or "").strip()
        estado = (dados.get("estado") or "").strip().upper()[:2]
        if not cidade:
            raise ErroDeValidacao("Informe sua cidade.", campo="cidade")
        if len(estado) != 2:
            raise ErroDeValidacao("Informe o estado (UF).", campo="estado")

        preferencia = Preferencia.buscar_por_usuario(usuario.id)
        if preferencia is None:
            preferencia = Preferencia(usuario_id=usuario.id)

        preferencia.orcamento = orcamento
        preferencia.cidade = cidade
        preferencia.estado = estado
        preferencia.definir_interesses(interesses)
        preferencia.salvar()

        return {
            "mensagem": "Preferências salvas!",
            "preferencias": preferencia.to_dict(),
        }
