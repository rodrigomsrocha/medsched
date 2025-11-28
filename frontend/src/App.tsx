import React, { useEffect, useMemo, useState } from "react";
import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import { Card } from "./components/ui/card";
import { Input } from "./components/ui/input";
import { Select } from "./components/ui/select";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

type Perfil = "PACIENTE" | "MEDICO" | "ADMIN";
type StatusConsulta = "AGENDADA" | "CONFIRMADA" | "CANCELADA" | "REALIZADA" | "REMARCADA";

type Usuario = {
  id: string;
  nome: string;
  email: string;
  telefone?: string | null;
  perfil: Perfil;
  especialidades?: string[] | null;
};

type Slot = {
  inicio: string;
  fim: string;
  bloqueado: boolean;
};

type Consulta = {
  id: string;
  paciente_id: string;
  paciente_nome: string;
  medico_id: string;
  medico_nome: string;
  especialidade?: string | null;
  especialidades?: string[] | null;
  inicio: string;
  fim: string;
  status: StatusConsulta;
  observacoes?: string | null;
};

type Session = {
  token: string;
  usuario: Usuario;
};

const statusTone: Record<StatusConsulta, { label: string; tone: "info" | "success" | "warning" | "danger" }> = {
  AGENDADA: { label: "Agendada", tone: "info" },
  CONFIRMADA: { label: "Confirmada", tone: "success" },
  CANCELADA: { label: "Cancelada", tone: "danger" },
  REALIZADA: { label: "Realizada", tone: "success" },
  REMARCADA: { label: "Remarcada", tone: "warning" },
};

async function fetchJson<T>(path: string, init?: RequestInit, token?: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers || {}),
    },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({} as any));
    throw new Error(detail.detail || res.statusText);
  }
  return res.json();
}

function formatDateTime(value: string) {
  const dt = new Date(value);
  const day = dt.toLocaleDateString("pt-BR", { weekday: "short", day: "2-digit", month: "short" });
  const hour = dt.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  return `${day} • ${hour}`;
}

function formatHourRange(slot: Slot) {
  const inicio = new Date(slot.inicio);
  const fim = new Date(slot.fim);
  const opts: Intl.DateTimeFormatOptions = { hour: "2-digit", minute: "2-digit" };
  return `${inicio.toLocaleTimeString("pt-BR", opts)} - ${fim.toLocaleTimeString("pt-BR", opts)}`;
}

function App() {
  const [session, setSession] = useState<Session | null>(() => {
    const stored = localStorage.getItem("medsched:session");
    return stored ? JSON.parse(stored) : null;
  });

  const [medicos, setMedicos] = useState<Usuario[]>([]);
  const [pacientes, setPacientes] = useState<Usuario[]>([]);
  const [consultas, setConsultas] = useState<Consulta[]>([]);
  const [slots, setSlots] = useState<Slot[]>([]);

  const [especializacaoFiltro, setEspecializacaoFiltro] = useState("");
  const [selectedMedicoPaciente, setSelectedMedicoPaciente] = useState<string | undefined>(undefined);

  const [novoMedico, setNovoMedico] = useState({ nome: "", email: "", telefone: "", especialidades: "", senha: "1234" });
  const [novoPaciente, setNovoPaciente] = useState({ nome: "", email: "", telefone: "", senha: "1234" });

  const [slotInicio, setSlotInicio] = useState("");
  const [slotDuracao, setSlotDuracao] = useState(30);

  const [remarcarId, setRemarcarId] = useState<string | null>(null);
  const [remarcarSlots, setRemarcarSlots] = useState<Slot[]>([]);
  const [remarcarEscolha, setRemarcarEscolha] = useState<string>("");

  const [loginForm, setLoginForm] = useState({ email: "", senha: "" });
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const especializacoes = useMemo(() => {
    const all = medicos.flatMap((m) => m.especialidades || []);
    return Array.from(new Set(all));
  }, [medicos]);

  const medicosFiltrados = useMemo(() => {
    if (!especializacaoFiltro) return medicos;
    return medicos.filter((m) => (m.especialidades || []).some((e) => e.toLowerCase().includes(especializacaoFiltro.toLowerCase())));
  }, [medicos, especializacaoFiltro]);

  useEffect(() => {
    (async () => {
      try {
        const med = await fetchJson<Usuario[]>("/medicos");
        setMedicos(med);
        if (!selectedMedicoPaciente) setSelectedMedicoPaciente(med[0]?.id);
      } catch (err) {
        console.error(err);
      }
    })();
  }, []);

  useEffect(() => {
    if (!session) return;
    if (session.usuario.perfil === "ADMIN") {
      carregarAdminDados();
    }
    if (session.usuario.perfil === "PACIENTE") {
      carregarPacienteDados(session.usuario.id, selectedMedicoPaciente);
    }
    if (session.usuario.perfil === "MEDICO") {
      carregarMedicoDados(session.usuario.id);
    }
  }, [session]);

  useEffect(() => {
    if (session?.usuario.perfil === "PACIENTE" && selectedMedicoPaciente) {
      carregarSlots(selectedMedicoPaciente);
    }
  }, [selectedMedicoPaciente, session?.usuario.perfil]);

  async function carregarAdminDados() {
    if (!session) return;
    try {
      const [med, pac, cons] = await Promise.all([
        fetchJson<Usuario[]>("/medicos", undefined, session.token),
        fetchJson<Usuario[]>("/pacientes", undefined, session.token),
        fetchJson<Consulta[]>("/consultas", undefined, session.token),
      ]);
      setMedicos(med);
      setPacientes(pac);
      setConsultas(cons);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function carregarPacienteDados(pacienteId: string, medicoId?: string) {
    if (!session) return;
    try {
      const cons = await fetchJson<Consulta[]>("/consultas", undefined, session.token);
      setConsultas(cons);
      if (medicoId) await carregarSlots(medicoId);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function carregarMedicoDados(medicoId: string) {
    if (!session) return;
    try {
      const [cons, slotsDisponiveis] = await Promise.all([
        fetchJson<Consulta[]>("/consultas", undefined, session.token),
        fetchJson<Slot[]>(`/agendas/${medicoId}/slots`),
      ]);
      setConsultas(cons);
      setSlots(slotsDisponiveis);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function carregarSlots(medicoId: string) {
    try {
      const s = await fetchJson<Slot[]>(`/agendas/${medicoId}/slots`);
      setSlots(s);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    try {
      setLoading(true);
      const data = await fetchJson<Session>(
        "/auth/login",
        { method: "POST", body: JSON.stringify(loginForm) },
        undefined
      );
      setSession(data);
      localStorage.setItem("medsched:session", JSON.stringify(data));
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    setSession(null);
    localStorage.removeItem("medsched:session");
  }

  async function criarMedicoAdmin(e: React.FormEvent) {
    e.preventDefault();
    if (!session) return;
    try {
      const payload = {
        nome: novoMedico.nome,
        email: novoMedico.email,
        telefone: novoMedico.telefone,
        senha: novoMedico.senha,
        especialidades: novoMedico.especialidades
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      };
      await fetchJson<Usuario>("/medicos", { method: "POST", body: JSON.stringify(payload) }, session.token);
      setNovoMedico({ nome: "", email: "", telefone: "", especialidades: "", senha: "1234" });
      await carregarAdminDados();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function criarPacienteAdmin(e: React.FormEvent) {
    e.preventDefault();
    if (!session) return;
    try {
      const payload = { ...novoPaciente };
      await fetchJson<Usuario>("/pacientes", { method: "POST", body: JSON.stringify(payload) }, session.token);
      setNovoPaciente({ nome: "", email: "", telefone: "", senha: "1234" });
      await carregarAdminDados();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function agendar(slot: Slot) {
    if (!session) return setError("Você precisa estar autenticado.");
    if (session.usuario.perfil !== "PACIENTE") return setError("Somente pacientes podem agendar.");
    try {
      setNotice(null);
      await fetchJson<Consulta>(
        "/consultas",
        {
          method: "POST",
          body: JSON.stringify({
            paciente_id: session.usuario.id,
            medico_id: selectedMedicoPaciente,
            inicio: slot.inicio,
            fim: slot.fim,
          }),
        },
        session.token
      );
      setNotice("Consulta registrada e aguardando confirmação do médico.");
      await carregarPacienteDados(session.usuario.id, selectedMedicoPaciente);
    } catch (err) {
      setNotice(null);
      setError((err as Error).message);
    }
  }

  async function atualizarConsulta(id: string, action: "confirmar" | "cancelar") {
    if (!session) return;
    try {
      await fetchJson<Consulta>(`/consultas/${id}/${action}`, { method: "POST" }, session.token);
      await recarregarPorPerfil();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function iniciarRemarcacao(consulta: Consulta) {
    try {
      const disponiveis = await fetchJson<Slot[]>(`/agendas/${consulta.medico_id}/slots`);
      if (disponiveis.length === 0) {
        setError("Sem horários livres para remarcação.");
        return;
      }
      setRemarcarId(consulta.id);
      setRemarcarSlots(disponiveis);
      setRemarcarEscolha(`${disponiveis[0].inicio}|${disponiveis[0].fim}`);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function confirmarRemarcacao() {
    if (!session || !remarcarId) return;
    const slot = remarcarSlots.find((s) => `${s.inicio}|${s.fim}` === remarcarEscolha);
    if (!slot) {
      setError("Selecione um horário válido.");
      return;
    }
    try {
      await fetchJson<Consulta>(
        `/consultas/${remarcarId}/remarcar`,
        { method: "POST", body: JSON.stringify({ novo_inicio: slot.inicio, novo_fim: slot.fim }) },
        session.token
      );
      setRemarcarId(null);
      setRemarcarEscolha("");
      setRemarcarSlots([]);
      await recarregarPorPerfil();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  // Atualização periódica para refletir backend sem refresh
  useEffect(() => {
    if (!session) return;
    const id = setInterval(() => {
      recarregarPorPerfil();
    }, 2000);
    return () => clearInterval(id);
  }, [session, selectedMedicoPaciente]);

  async function recarregarPorPerfil() {
    if (!session) return;
    if (session.usuario.perfil === "ADMIN") return carregarAdminDados();
    if (session.usuario.perfil === "PACIENTE") return carregarPacienteDados(session.usuario.id, selectedMedicoPaciente);
    if (session.usuario.perfil === "MEDICO") return carregarMedicoDados(session.usuario.id);
  }

  async function criarSlotMedico(e: React.FormEvent) {
    e.preventDefault();
    if (!session || session.usuario.perfil !== "MEDICO") return;
    if (!slotInicio) {
      setError("Informe uma data/hora de início.");
      return;
    }
    const inicio = new Date(slotInicio);
    const fim = new Date(inicio.getTime() + slotDuracao * 60000);
    try {
      await fetchJson<Slot>(
        `/agendas/${session.usuario.id}/slots`,
        { method: "POST", body: JSON.stringify({ inicio, fim, bloqueado: false }) },
        session.token
      );
      setSlotInicio("");
      await carregarMedicoDados(session.usuario.id);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  const consultasExibidas = useMemo(() => {
    if (session?.usuario.perfil === "PACIENTE") return consultas;
    if (session?.usuario.perfil === "MEDICO") return consultas;
    return consultas; // admin vê todas
  }, [consultas, session?.usuario.perfil]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-8">
        <div>
          <p className="text-sm uppercase tracking-[0.25em] text-primary-600 font-semibold">MedSched</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">Agendamentos em tempo real</h1>
          <p className="text-slate-600">FastAPI + React com papéis de Admin, Médico e Paciente.</p>
        </div>
        {session ? (
          <div className="flex items-center gap-3">
            <div className="rounded-full bg-primary-50 px-4 py-2 text-primary-700 font-semibold shadow-brand">
              {session.usuario.nome} · {session.usuario.perfil}
            </div>
            <Button variant="secondary" onClick={logout}>
              Sair
            </Button>
          </div>
        ) : (
          <span className="rounded-full bg-primary-50 px-4 py-2 text-primary-700 font-semibold shadow-brand">
            Acesso com login simples
          </span>
        )}
      </header>

      <main className="mx-auto max-w-6xl px-6 pb-16 space-y-6">
        {error && (
          <div className="flex items-start justify-between rounded-lg border border-rose-100 bg-rose-50 px-4 py-3 text-rose-700">
            <span>{error}</span>
            <button className="text-rose-500" onClick={() => setError(null)}>
              ✕
            </button>
          </div>
        )}
        {notice && (
          <div className="flex items-start justify-between rounded-lg border border-blue-100 bg-blue-50 px-4 py-3 text-blue-700">
            <span>{notice}</span>
            <button className="text-blue-500" onClick={() => setNotice(null)}>
              ✕
            </button>
          </div>
        )}

        {!session && (
          <Card title="Entrar" description="Use o e-mail e senha fornecidos (admin@medsched.com, ana@clinic.com, joao@email.com etc)">
            <form className="grid gap-3 md:grid-cols-3" onSubmit={handleLogin}>
              <Input
                label="E-mail"
                value={loginForm.email}
                onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })}
                required
              />
              <Input
                label="Senha"
                type="password"
                value={loginForm.senha}
                onChange={(e) => setLoginForm({ ...loginForm, senha: e.target.value })}
                required
              />
              <div className="flex items-end">
                <Button type="submit" className="w-full" loading={loading}>
                  Entrar
                </Button>
              </div>
            </form>
          </Card>
        )}

        {session?.usuario.perfil === "ADMIN" && (
          <div className="grid gap-4 md:grid-cols-2">
            <Card title="Cadastrar médico" description="Inclua novos profissionais com especializações múltiplas.">
              <form className="grid gap-3" onSubmit={criarMedicoAdmin}>
                <Input label="Nome" value={novoMedico.nome} onChange={(e) => setNovoMedico({ ...novoMedico, nome: e.target.value })} required />
                <Input label="E-mail" value={novoMedico.email} onChange={(e) => setNovoMedico({ ...novoMedico, email: e.target.value })} required />
                <Input label="Telefone" value={novoMedico.telefone} onChange={(e) => setNovoMedico({ ...novoMedico, telefone: e.target.value })} />
                <Input
                  label="Especializações"
                  description="Separe por vírgula (ex: Cardiologia, Clínica Geral)"
                  value={novoMedico.especialidades}
                  onChange={(e) => setNovoMedico({ ...novoMedico, especialidades: e.target.value })}
                />
                <Input label="Senha" type="password" value={novoMedico.senha} onChange={(e) => setNovoMedico({ ...novoMedico, senha: e.target.value })} required />
                <Button type="submit">Salvar médico</Button>
              </form>
            </Card>
            <Card title="Cadastrar paciente" description="Crie contas para pacientes acessarem a agenda.">
              <form className="grid gap-3" onSubmit={criarPacienteAdmin}>
                <Input label="Nome" value={novoPaciente.nome} onChange={(e) => setNovoPaciente({ ...novoPaciente, nome: e.target.value })} required />
                <Input label="E-mail" value={novoPaciente.email} onChange={(e) => setNovoPaciente({ ...novoPaciente, email: e.target.value })} required />
                <Input label="Telefone" value={novoPaciente.telefone} onChange={(e) => setNovoPaciente({ ...novoPaciente, telefone: e.target.value })} />
                <Input label="Senha" type="password" value={novoPaciente.senha} onChange={(e) => setNovoPaciente({ ...novoPaciente, senha: e.target.value })} required />
                <Button type="submit">Salvar paciente</Button>
              </form>
            </Card>
          </div>
        )}

        {session?.usuario.perfil === "PACIENTE" && (
          <>
            <Card
              title="Buscar médico"
              description="Filtre por especialização e escolha o profissional para agendar."
              action={<Badge tone="info">{especializacoes.length} especialidades</Badge>}
            >
              <div className="grid gap-3 md:grid-cols-3">
                <Select label="Especialização" value={especializacaoFiltro} onChange={(e) => setEspecializacaoFiltro(e.target.value)}>
                  <option value="">Todas</option>
                  {especializacoes.map((esp) => (
                    <option key={esp} value={esp}>
                      {esp}
                    </option>
                  ))}
                </Select>
                <Select
                  label="Médico"
                  value={selectedMedicoPaciente}
                  onChange={(e) => setSelectedMedicoPaciente(e.target.value)}
                  description="Lista filtrada pela especialização"
                >
                  {medicosFiltrados.map((med) => (
                    <option key={med.id} value={med.id}>
                      {med.nome} · {(med.especialidades || []).join(", ") || "Clínico"}
                    </option>
                  ))}
                </Select>
              </div>
            </Card>

            <Card
              title="Horários disponíveis"
              description="Slots livres do médico selecionado."
              action={<Badge tone="info">{slots.length} horários</Badge>}
            >
              {slots.length === 0 ? (
                <p className="text-slate-600">Nenhum horário livre no momento.</p>
              ) : (
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {slots.map((slot) => (
                    <div key={`${slot.inicio}-${slot.fim}`} className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
                      <p className="text-sm text-slate-500">{formatDateTime(slot.inicio)}</p>
                      <p className="text-lg font-semibold text-slate-900">{formatHourRange(slot)}</p>
                      <Button className="mt-3 w-full" onClick={() => agendar(slot)}>
                        Agendar
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </>
        )}

        {session?.usuario.perfil === "MEDICO" && (
          <div className="grid gap-4 md:grid-cols-2">
            <Card title="Liberar horário" description="Crie slots livres na sua agenda">
              <form className="grid gap-3" onSubmit={criarSlotMedico}>
                <Input
                  label="Início"
                  type="datetime-local"
                  value={slotInicio}
                  onChange={(e) => setSlotInicio(e.target.value)}
                  required
                />
                <Input
                  label="Duração (min)"
                  type="number"
                  value={slotDuracao}
                  min={15}
                  max={240}
                  onChange={(e) => setSlotDuracao(Number(e.target.value))}
                />
                <Button type="submit">Adicionar slot</Button>
              </form>
            </Card>
            <Card title="Slots ativos" description="Horários livres já publicados" action={<Badge tone="info">{slots.length}</Badge>}>
              {slots.length === 0 ? (
                <p className="text-slate-600">Nenhum slot cadastrado.</p>
              ) : (
                <ul className="space-y-2">
                  {slots.map((slot) => (
                    <li key={`${slot.inicio}-${slot.fim}`} className="flex items-center justify-between rounded-lg border border-slate-100 bg-white px-4 py-2 shadow-sm">
                      <span className="text-sm text-slate-700">{formatDateTime(slot.inicio)} ({formatHourRange(slot)})</span>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>
        )}

        {session && (
          <Card
            title="Consultas"
            description="Gerencie status, cancelamentos e remarcações"
            action={<Badge tone="info">{consultasExibidas.length} consultas</Badge>}
          >
            {consultasExibidas.length === 0 ? (
              <p className="text-slate-600">Sem consultas registradas.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200 text-sm">
                  <thead>
                    <tr className="text-left text-slate-600">
                      <th className="py-3">Paciente</th>
                      <th className="py-3">Médico</th>
                      <th className="py-3">Horário</th>
                      <th className="py-3">Status</th>
                      <th className="py-3">Ações</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {consultasExibidas.map((consulta) => (
                      <tr key={consulta.id} className="align-top">
                        <td className="py-3">
                          <div className="font-semibold text-slate-900">{consulta.paciente_nome}</div>
                          <div className="text-xs text-slate-500">#{consulta.paciente_id.slice(0, 6)}</div>
                        </td>
                        <td className="py-3">
                          <div className="font-semibold text-slate-900">{consulta.medico_nome}</div>
                          <div className="text-xs text-slate-500">{(consulta.especialidades || []).join(", ")}</div>
                        </td>
                        <td className="py-3">
                          <div className="font-semibold text-slate-900">{formatDateTime(consulta.inicio)}</div>
                          <div className="text-xs text-slate-500">até {formatDateTime(consulta.fim)}</div>
                        </td>
                        <td className="py-3">
                          <Badge tone={statusTone[consulta.status].tone}>{statusTone[consulta.status].label}</Badge>
                        </td>
                        <td className="py-3">
                          <div className="flex flex-wrap gap-2">
                            {consulta.status === "AGENDADA" &&
                              session?.usuario.perfil === "MEDICO" &&
                              session.usuario.id === consulta.medico_id && (
                                <Button
                                  variant="primary"
                                  onClick={() => atualizarConsulta(consulta.id, "confirmar")}
                                  disabled={consulta.status === "CANCELADA"}
                                >
                                  Confirmar
                                </Button>
                              )}
                            {consulta.status !== "CANCELADA" && (
                              <Button
                                variant="secondary"
                                onClick={() => atualizarConsulta(consulta.id, "cancelar")}
                                disabled={consulta.status === "CANCELADA"}
                              >
                                Cancelar
                              </Button>
                            )}
                            <Button
                              variant="ghost"
                              onClick={() => iniciarRemarcacao(consulta)}
                              disabled={consulta.status === "CANCELADA"}
                            >
                              Remarcar
                            </Button>
                            {remarcarId === consulta.id && remarcarSlots.length > 0 && (
                              <div className="flex flex-wrap items-center gap-2">
                                <Select value={remarcarEscolha} onChange={(e) => setRemarcarEscolha(e.target.value)}>
                                  {remarcarSlots.map((slot) => (
                                    <option key={`${slot.inicio}-${slot.fim}`} value={`${slot.inicio}|${slot.fim}`}>
                                      {formatDateTime(slot.inicio)} ({formatHourRange(slot)})
                                    </option>
                                  ))}
                                </Select>
                                <Button variant="primary" onClick={confirmarRemarcacao}>
                                  Salvar
                                </Button>
                                <Button variant="ghost" onClick={() => setRemarcarId(null)}>
                                  Fechar
                                </Button>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        )}
      </main>
    </div>
  );
}

export default App;
