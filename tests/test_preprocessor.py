"""Testes unitarios para o preprocessador"""

import pytest
from datetime import datetime
from app.services.preprocessor import IncidentPreprocessor


class TestIncidentPreprocessor:
    """Testes para a classe IncidentPreprocessor"""

    def test_normalize_whitespace(self, preprocessor):
        """Deve normalizar espacos duplicados"""
        text = "Texto   com    muitos     espacos"
        result = preprocessor._normalize_whitespace(text)
        assert result == "Texto com muitos espacos"

    def test_normalize_whitespace_newlines(self, preprocessor):
        """Deve normalizar quebras de linha"""
        text = "Texto\ncom\n\nquebras\n\n\nde linha"
        result = preprocessor._normalize_whitespace(text)
        assert result == "Texto com quebras de linha"

    def test_normalize_whitespace_trim(self, preprocessor):
        """Deve remover espacos no inicio e fim"""
        text = "   texto com espacos   "
        result = preprocessor._normalize_whitespace(text)
        assert result == "texto com espacos"

    def test_clean_special_chars_keeps_punctuation(self, preprocessor):
        """Deve manter pontuacao basica"""
        text = "Texto com pontuacao: virgula, ponto. Exclamacao! Interrogacao?"
        result = preprocessor._clean_special_chars(text)
        assert ":" in result
        assert "," in result
        assert "." in result
        assert "!" in result
        assert "?" in result

    def test_clean_special_chars_keeps_accents(self, preprocessor):
        """Deve manter acentuacao portuguesa"""
        text = "Sao Paulo, Brasilia, acao, informacao"
        result = preprocessor._clean_special_chars(text)
        assert "Sao" in result
        assert "Brasilia" in result
        assert "acao" in result

    def test_clean_special_chars_removes_invalid(self, preprocessor):
        """Deve remover caracteres invalidos"""
        text = "Texto com #hashtag e $dolar e %percentual"
        result = preprocessor._clean_special_chars(text)
        assert "#" not in result
        assert "$" not in result
        assert "%" not in result

    def test_preprocess_returns_tuple(self, preprocessor):
        """Deve retornar tupla com texto e data"""
        text = "Incidente de teste"
        result = preprocessor.preprocess(text)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_preprocess_returns_reference_date(self, preprocessor):
        """Deve retornar data de referencia no formato correto"""
        text = "Incidente de teste"
        _, reference_date = preprocessor.preprocess(text)
        assert reference_date == "2025-02-04"

    def test_preprocess_full_pipeline(self, preprocessor):
        """Deve processar texto completo corretamente"""
        text = "   ONTEM   houve um incidente #grave   "
        processed_text, _ = preprocessor.preprocess(text)
        # Deve conter data resolvida no formato ISO
        assert "2025-02-03" in processed_text
        assert "grave" in processed_text

    def test_set_reference_date(self):
        """Deve permitir alterar data de referencia"""
        prep = IncidentPreprocessor()
        new_date = datetime(2025, 1, 15, 10, 30, 0)
        prep.set_reference_date(new_date)
        _, reference_date = prep.preprocess("teste")
        assert reference_date == "2025-01-15"


class TestDateResolution:
    """Testes para resolução de datas"""

    @pytest.fixture
    def preprocessor(self):
        """Preprocessor com data fixa para testes"""
        prep = IncidentPreprocessor()
        prep.set_reference_date(datetime(2025, 2, 4, 12, 0, 0))
        return prep

    # Testes para datas relativas
    def test_resolve_hoje(self, preprocessor):
        """Deve resolver 'hoje' para data atual"""
        text = "Hoje houve um incidente"
        result, _ = preprocessor.preprocess(text)
        assert "2025-02-04" in result

    def test_resolve_hoje_com_horario(self, preprocessor):
        """Deve resolver 'hoje às 10h' com horário"""
        text = "Hoje às 10h houve um incidente"
        result, _ = preprocessor.preprocess(text)
        assert "2025-02-04" in result
        assert "10:00" in result

    def test_resolve_hoje_com_horario_minutos(self, preprocessor):
        """Deve resolver 'hoje às 10:30' com minutos"""
        text = "Hoje às 10:30 houve um incidente"
        result, _ = preprocessor.preprocess(text)
        assert "2025-02-04" in result
        assert "10:30" in result

    def test_resolve_ontem(self, preprocessor):
        """Deve resolver 'ontem' para dia anterior"""
        text = "Ontem houve um incidente"
        result, _ = preprocessor.preprocess(text)
        assert "2025-02-03" in result

    def test_resolve_ontem_com_horario(self, preprocessor):
        """Deve resolver 'ontem às 14h' com horário"""
        text = "Ontem às 14h houve um incidente"
        result, _ = preprocessor.preprocess(text)
        assert "2025-02-03" in result
        assert "14:00" in result

    def test_resolve_anteontem(self, preprocessor):
        """Deve resolver 'anteontem' para 2 dias atrás"""
        text = "Anteontem houve um incidente"
        result, _ = preprocessor.preprocess(text)
        assert "2025-02-02" in result

    def test_resolve_ontem_pela_manha(self, preprocessor):
        """Deve resolver 'ontem pela manhã' com horário padrão"""
        text = "Ontem pela manhã houve um incidente"
        result, _ = preprocessor.preprocess(text)
        assert "2025-02-03" in result
        assert "09:00" in result

    def test_resolve_ontem_a_tarde(self, preprocessor):
        """Deve resolver 'ontem à tarde' com horário padrão"""
        text = "Ontem à tarde houve um incidente"
        result, _ = preprocessor.preprocess(text)
        assert "2025-02-03" in result
        assert "14:00" in result

    def test_resolve_ontem_a_noite(self, preprocessor):
        """Deve resolver 'ontem à noite' com horário padrão"""
        text = "Ontem à noite houve um incidente"
        result, _ = preprocessor.preprocess(text)
        assert "2025-02-03" in result
        assert "20:00" in result

    # Testes para datas DD/MM/YYYY
    def test_resolve_data_ddmmyyyy(self, preprocessor):
        """Deve resolver data no formato DD/MM/YYYY"""
        text = "No dia 27/01/2025 houve um incidente"
        result, _ = preprocessor.preprocess(text)
        assert "2025-01-27" in result

    def test_resolve_data_ddmmyy(self, preprocessor):
        """Deve resolver data no formato DD/MM/YY"""
        text = "No dia 27/01/25 houve um incidente"
        result, _ = preprocessor.preprocess(text)
        assert "2025-01-27" in result

    def test_resolve_data_ddmmyyyy_com_prefixo(self, preprocessor):
        """Deve resolver data com prefixo 'dia'"""
        text = "Dia 15/03/2025 houve um incidente"
        result, _ = preprocessor.preprocess(text)
        assert "2025-03-15" in result

    # Testes para datas DD/MM (sem ano)
    def test_resolve_data_ddmm_passado(self, preprocessor):
        """Deve resolver data DD/MM no passado"""
        text = "Dia 27/01 houve um incidente"
        result, _ = preprocessor.preprocess(text)
        assert "2025-01-27" in result

    def test_resolve_data_ddmm_futuro_usa_ano_anterior(self, preprocessor):
        """Deve usar ano anterior se data DD/MM seria futura"""
        # Data de referência é 04/02/2025
        # 15/03 seria futuro, então deve usar 2024
        text = "Dia 15/03 houve um incidente"
        result, _ = preprocessor.preprocess(text)
        assert "2024-03-15" in result

    # Testes para datas por extenso
    def test_resolve_data_extenso(self, preprocessor):
        """Deve resolver data por extenso"""
        text = "No dia 15 de janeiro houve um incidente"
        result, _ = preprocessor.preprocess(text)
        assert "2025-01-15" in result

    def test_resolve_data_extenso_com_ano(self, preprocessor):
        """Deve resolver data por extenso com ano"""
        text = "No dia 20 de março de 2024 houve um incidente"
        result, _ = preprocessor.preprocess(text)
        assert "2024-03-20" in result

    def test_resolve_data_extenso_mes_abreviado(self, preprocessor):
        """Deve resolver data com mês abreviado"""
        text = "No dia 10 de jan houve um incidente"
        result, _ = preprocessor.preprocess(text)
        assert "2025-01-10" in result

    def test_resolve_data_extenso_marco_com_cedilha(self, preprocessor):
        """Deve resolver 'março' com cedilha"""
        text = "No dia 5 de março de 2025 houve um incidente"
        result, _ = preprocessor.preprocess(text)
        assert "2025-03-05" in result

    # Testes de normalização de horário
    def test_normalize_horario_h(self, preprocessor):
        """Deve normalizar '10h' para '10:00'"""
        text = "no dia 2025-02-04 às 10h houve incidente"
        result, _ = preprocessor.preprocess(text)
        assert "10:00" in result

    def test_normalize_horario_horas(self, preprocessor):
        """Deve normalizar '10 horas' para '10:00'"""
        text = "no dia 2025-02-04 às 10 horas houve incidente"
        result, _ = preprocessor.preprocess(text)
        assert "10:00" in result

    # Testes de caso real
    def test_caso_real_hoje_10h_campinas(self, preprocessor):
        """Teste com entrada real: hoje às 10h em Campinas"""
        text = "Hoje às 10h, na sede de Campinas, houve uma falha no servidor"
        result, ref_date = preprocessor.preprocess(text)

        assert "2025-02-04" in result
        assert "10:00" in result
        assert "Campinas" in result
        assert ref_date == "2025-02-04"

    def test_caso_real_dia_2701(self, preprocessor):
        """Teste com entrada real: dia 27/01"""
        text = "Dia 27/01 às 10h, na sede de Campinas, houve uma falha"
        result, _ = preprocessor.preprocess(text)

        assert "2025-01-27" in result
        assert "10:00" in result

    def test_caso_real_ontem_14h_sao_paulo(self, preprocessor):
        """Teste com entrada real: ontem às 14h em São Paulo"""
        text = "Ontem às 14h, no escritório de São Paulo, houve uma falha no servidor"
        result, _ = preprocessor.preprocess(text)

        assert "2025-02-03" in result
        assert "14:00" in result
        assert "Paulo" in result

    # Testes de edge cases
    def test_data_invalida_mantida(self, preprocessor):
        """Data inválida deve ser mantida como está"""
        text = "Dia 32/13/2025 houve um incidente"
        result, _ = preprocessor.preprocess(text)
        # Não deve crashar, mantém original
        assert "32/13/2025" in result or "incidente" in result

    def test_texto_sem_data(self, preprocessor):
        """Texto sem data deve passar normalmente"""
        text = "Houve um incidente no servidor de São Paulo"
        result, ref_date = preprocessor.preprocess(text)

        assert "servidor" in result
        assert "Paulo" in result
        assert ref_date == "2025-02-04"

    def test_multiplas_datas_no_texto(self, preprocessor):
        """Deve resolver múltiplas datas no mesmo texto"""
        text = "O incidente de ontem às 10h foi similar ao de dia 15/01"
        result, _ = preprocessor.preprocess(text)

        assert "2025-02-03" in result  # ontem
        assert "2025-01-15" in result  # 15/01


class TestPreprocessorMesesPortugues:
    """Testes para meses em português"""

    @pytest.fixture
    def preprocessor(self):
        prep = IncidentPreprocessor()
        prep.set_reference_date(datetime(2025, 6, 15, 12, 0, 0))
        return prep

    def test_todos_os_meses(self, preprocessor):
        """Deve reconhecer todos os meses em português"""
        meses = [
            ("janeiro", "01"),
            ("fevereiro", "02"),
            ("março", "03"),
            ("abril", "04"),
            ("maio", "05"),
            ("junho", "06"),
            ("julho", "07"),
            ("agosto", "08"),
            ("setembro", "09"),
            ("outubro", "10"),
            ("novembro", "11"),
            ("dezembro", "12"),
        ]

        for mes_nome, mes_num in meses:
            text = f"No dia 10 de {mes_nome} de 2025 houve incidente"
            result, _ = preprocessor.preprocess(text)
            assert f"2025-{mes_num}-10" in result, f"Falhou para {mes_nome}"

    def test_meses_abreviados(self, preprocessor):
        """Deve reconhecer meses abreviados"""
        meses_abrev = [
            ("jan", "01"),
            ("fev", "02"),
            ("mar", "03"),
            ("abr", "04"),
            ("mai", "05"),
            ("jun", "06"),
            ("jul", "07"),
            ("ago", "08"),
            ("set", "09"),
            ("out", "10"),
            ("nov", "11"),
            ("dez", "12"),
        ]

        for mes_abrev, mes_num in meses_abrev:
            text = f"No dia 5 de {mes_abrev} de 2025 houve incidente"
            result, _ = preprocessor.preprocess(text)
            assert f"2025-{mes_num}-05" in result, f"Falhou para {mes_abrev}"
