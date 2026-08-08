"""
bs.py — Precificação Black-Scholes-Merton (preço, delta, gamma) com dividend
yield contínuo.

Este arquivo NÃO estava entre os uploads (motor_calculo.py e
gerar_dados_exemplo.py fazem `import bs` mas o módulo em si não veio junto).
Reconstruído aqui a partir das assinaturas de chamada usadas nos dois
arquivos:

    bs.preco_teorico(S, K, T, r, sigma, tipo, q)   # tipo: "CALL" | "PUT"
    bs.delta(S, K, T, r, sigma, tipo, q)
    bs.gamma(S, K, T, r, sigma, q)

São as fórmulas fechadas padrão de Black-Scholes-Merton — não há ambiguidade
de implementação aqui (ao contrário da lógica de GEX/dashboard, que tem
escolhas de design específicas, isto é matemática de livro-texto). Sem
dependências além da stdlib (usa math.erf para a CDF normal, então não
precisa de scipy).

Se o seu bs.py original tiver alguma convenção diferente (ex.: outra
contagem de dias, ou T já vindo em outra unidade), é só substituir este
arquivo mantendo as mesmas assinaturas — nada mais no pipeline muda.
"""

import math


def _norm_cdf(x: float) -> float:
    """CDF da normal padrão via função erro (evita dependência de scipy)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_pdf(x: float) -> float:
    """PDF da normal padrão."""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _d1_d2(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0):
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return d1, d2


def preco_teorico(S: float, K: float, T: float, r: float, sigma: float,
                   tipo: str, q: float = 0.0) -> float:
    """Preço teórico Black-Scholes-Merton. `tipo`: 'CALL' ou 'PUT'.

    T em anos. Se T<=0 ou sigma<=0, cai para o valor intrínseco (sem
    otimismo de tempo a esperar)."""
    if T <= 0 or sigma <= 0:
        intrinseco = (S - K) if tipo == "CALL" else (K - S)
        return max(0.0, intrinseco)

    d1, d2 = _d1_d2(S, K, T, r, sigma, q)
    if tipo == "CALL":
        return S * math.exp(-q * T) * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
    else:
        return K * math.exp(-r * T) * _norm_cdf(-d2) - S * math.exp(-q * T) * _norm_cdf(-d1)


def delta(S: float, K: float, T: float, r: float, sigma: float,
          tipo: str, q: float = 0.0) -> float:
    """Delta Black-Scholes-Merton. `tipo`: 'CALL' ou 'PUT'."""
    if T <= 0 or sigma <= 0:
        if tipo == "CALL":
            return 1.0 if S > K else 0.0
        return -1.0 if S < K else 0.0

    d1, _ = _d1_d2(S, K, T, r, sigma, q)
    if tipo == "CALL":
        return math.exp(-q * T) * _norm_cdf(d1)
    else:
        return math.exp(-q * T) * (_norm_cdf(d1) - 1.0)


def gamma(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
    """Gamma Black-Scholes-Merton (idêntico para call e put)."""
    if T <= 0 or sigma <= 0:
        return 0.0

    d1, _ = _d1_d2(S, K, T, r, sigma, q)
    return math.exp(-q * T) * _norm_pdf(d1) / (S * sigma * math.sqrt(T))
