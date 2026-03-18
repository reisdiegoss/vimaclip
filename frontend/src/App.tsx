import { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Download,
  AlertCircle,
  Zap,
  ArrowLeft,
  ArrowRight,
  Monitor,
  Maximize2,
  Clock,
  Plus,
  Trash2,
  Globe,
  MessageSquare,
  FileCode,
  Settings
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// Configuração do Backend
const API_BASE_URL = 'http://localhost:8001/api';

// Interfaces
interface Segment {
  start: string;
  end: string;
}

interface ProcessedVideo {
  id: number;
  title: string;
  clips: Array<{
    id: number;
    video_path: string;
    transcription: any;
    start_time: string;
    end_time: string;
  }>;
}

function App() {
  // --- Estados ---
  const [activeTab, setActiveTab] = useState<'config' | 'projects'>('config');
  const [videoUrl, setVideoUrl] = useState('');
  const [format, setFormat] = useState('vertical');
  const [subtitlesActive, setSubtitlesActive] = useState(false);
  const [showTranscription, setShowTranscription] = useState(false);
  const [segments, setSegments] = useState<Segment[]>([{ start: '00:00', end: '00:30' }]);
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [result, setResult] = useState<ProcessedVideo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [projects, setProjects] = useState<any[]>([]);
  const [selectedClipIndex, setSelectedClipIndex] = useState(0);

  // --- Máscara de Tempo (MM:SS) ---
  const formatTime = (value: string) => {
    const digits = value.replace(/\D/g, '').slice(0, 4);
    if (digits.length <= 2) return digits;
    return `${digits.slice(0, 2)}:${digits.slice(2)}`;
  };

  // --- Helpers ---
  const addSegment = () => setSegments([...segments, { start: '00:30', end: '01:00' }]);
  const removeSegment = (index: number) => segments.length > 1 && setSegments(segments.filter((_, i) => i !== index));
  const updateSegment = (index: number, field: keyof Segment, value: string) => {
    const newSegments = [...segments];
    newSegments[index][field] = value;
    setSegments(newSegments);
  };

  const addLog = (msg: string) => setLogs(prev => [...prev.slice(-4), msg]);

  const fetchProjects = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/videos`);
      setProjects(response.data);
    } catch (err) {
      console.error("Erro ao carregar projetos:", err);
    }
  };

  const deleteProject = async (id: number) => {
    try {
      await axios.delete(`${API_BASE_URL}/videos/${id}`);
      setProjects(prev => prev.filter(p => p.id !== id));
      if (result?.id === id) setResult(null);
    } catch (err) {
      console.error("Erro ao deletar projeto:", err);
    }
  };

  const clearHistory = async () => {
    if (!confirm("Deseja realmente apagar todo o histórico?")) return;
    try {
      await axios.delete(`${API_BASE_URL}/videos`);
      setProjects([]);
      setResult(null);
    } catch (err) {
      console.error("Erro ao limpar histórico:", err);
    }
  };

  useEffect(() => {
    if (activeTab === 'projects') fetchProjects();
  }, [activeTab]);

  const handleProcess = async () => {
    if (!videoUrl) {
      setError('Por favor, insira uma URL de vídeo para iniciar.');
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    setSelectedClipIndex(0);
    setLogs(['Iniciando pipeline de corte direto...']);

    const payload = {
      video_url: videoUrl,
      segments: segments,
      format,
      burn_subtitles: subtitlesActive,
      clip_model: 'auto',
      genre: 'auto',
      ai_instructions: ''
    };

    try {
      setTimeout(() => addLog('Baixando vídeo da fonte...'), 1000);
      setTimeout(() => addLog('Restaurando pipeline neuronal...'), 3000);
      setTimeout(() => addLog('Iniciando Smart Director IA...'), 6000);

      const response = await axios.post(`${API_BASE_URL}/videos/process`, payload);
      const details = await axios.get(`${API_BASE_URL}/videos/${response.data.video_id}`);
      setResult(details.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ocorreu um erro no processamento.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-[#0a0a0c] font-sans selection:bg-[#00f2ea]/30 text-white">
      <div className="fixed top-0 left-0 w-full h-full pointer-events-none -z-10 bg-[#0d1117]" />
      <div className="fixed -top-[10%] -left-[10%] w-[60%] h-[60%] bg-[#00f2ea]/5 blur-[220px] rounded-full pointer-events-none" />
      <div className="fixed -bottom-[10%] -right-[10%] w-[60%] h-[60%] bg-blue-500/5 blur-[220px] rounded-full pointer-events-none" />

      <motion.div initial={{ opacity: 0, y: 40 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-[1180px] bg-[#161b22]/95 backdrop-blur-3xl border border-white/10 rounded-[3rem] shadow-[0_120px_250px_-50px_rgba(0,0,0,1)] flex flex-col overflow-hidden relative">
        <header className="px-12 h-24 flex items-center justify-between border-b border-white/5 bg-white/[0.01]">
          <div className="flex items-center gap-4">
            <div className="w-11 h-11 bg-gradient-to-tr from-[#00f2ea] to-[#00d8ff] rounded-[14px] flex items-center justify-center shadow-lg shadow-[#00f2ea]/20">
              <Zap size={24} fill="#0d1117" className="text-[#0d1117]" />
            </div>
            <div className="flex flex-col">
              <span className="text-[19px] font-black tracking-widest uppercase leading-none">VIMA CLIP</span>
              <span className="text-[9px] text-[#00f2ea] font-black uppercase tracking-[0.4em] mt-1.5 opacity-80">BACKEND ENGINE v8.1</span>
            </div>
          </div>
          <div className="flex items-center gap-10">
            <div className="flex items-center gap-2 text-[10px] font-black text-white/30 uppercase tracking-widest bg-white/[0.03] px-5 py-2.5 rounded-full border border-white/5">
              <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse shadow-[0_0_10px_#22c55e]" /> Servidor Online
            </div>
            <div className="flex items-center gap-3 bg-white/5 border border-white/5 p-1 rounded-full cursor-not-allowed">
              <div className="w-9 h-9 rounded-full bg-zinc-800 flex items-center justify-center border border-white/10">
                <Settings size={18} className="text-white/20" />
              </div>
            </div>
          </div>
        </header>

        <div className="flex flex-1 overflow-hidden">
          <div className={`flex-1 p-12 flex flex-col gap-12 overflow-y-auto custom-scrollbar bg-white/[0.01] transition-all duration-500 ${result ? 'max-w-[650px]' : ''}`}>
            <div className="flex gap-12 text-[13px] font-black uppercase tracking-widest border-b border-white/5">
              <div onClick={() => setActiveTab('config')} className="relative pb-6 cursor-pointer">
                <span className={`transition-colors ${activeTab === 'config' ? 'text-white' : 'text-white/20 hover:text-white/50'}`}>Configuração</span>
                {activeTab === 'config' && <motion.div layoutId="tab" className="absolute bottom-0 left-0 w-full h-[3px] bg-[#00f2ea] shadow-[0_0_20px_#00f2ea]" />}
              </div>
              <div onClick={() => setActiveTab('projects')} className="relative pb-6 cursor-pointer">
                <span className={`transition-colors ${activeTab === 'projects' ? 'text-white' : 'text-white/20 hover:text-white/50'}`}>Histórico</span>
                {activeTab === 'projects' && <motion.div layoutId="tab" className="absolute bottom-0 left-0 w-full h-[3px] bg-[#00f2ea] shadow-[0_0_20px_#00f2ea]" />}
              </div>
            </div>

            {activeTab === 'config' ? (
              <>
                <div className="space-y-4">
                  <div className="flex items-center justify-between pl-1">
                    <label className="text-[12px] font-black text-white/40 uppercase tracking-[0.2em]">Fonte do Vídeo</label>
                    <span className="text-[9px] font-bold text-[#00f2ea]/40 uppercase tracking-widest">URL</span>
                  </div>
                  <div className="relative group">
                    <input type="text" placeholder="Cole o link do vídeo aqui..." value={videoUrl} onChange={(e) => setVideoUrl(e.target.value)} className="w-full bg-[#0d1117] border border-white/5 rounded-[1.5rem] px-8 py-6 text-sm font-bold focus:outline-none focus:ring-1 focus:ring-[#00f2ea]/40 transition-all placeholder:opacity-10 shadow-inner group-hover:border-white/10" />
                    <Globe size={20} className="absolute right-8 top-1/2 -translate-y-1/2 text-white/5 group-hover:text-[#00f2ea]/20 transition-colors" />
                  </div>
                </div>

                <section className="space-y-5">
                  <label className="text-[12px] font-black text-white/40 uppercase tracking-[0.2em]">Formato de Exportação</label>
                  <div className="flex gap-5">
                    {[
                      { id: 'vertical', label: '9:16', desc: 'Reels/Shorts', icon: <Monitor size={22} className="rotate-90" /> },
                      { id: 'square', label: '1:1', desc: 'Social Feed', icon: <Maximize2 size={22} /> },
                      { id: 'horizontal', label: '16:9', desc: 'YouTube', icon: <Monitor size={22} /> }
                    ].map(f => (
                      <button key={f.id} onClick={() => setFormat(f.id)} className={`flex-1 flex flex-col items-center text-center gap-3 p-7 rounded-3xl border transition-all ${format === f.id ? 'bg-[#00f2ea]/10 border-[#00f2ea] text-[#00f2ea] shadow-[0_20px_40px_-10px_rgba(0,242,234,0.2)]' : 'bg-[#0d1117]/60 border-white/5 text-white/20 hover:border-white/10 hover:bg-white/[0.02]'}`}>
                        <div className={`transition-transform duration-500 ${format === f.id ? 'scale-110' : ''}`}>{f.icon}</div>
                        <div className="flex flex-col gap-1">
                          <span className="text-[11px] font-black uppercase tracking-widest">{f.label}</span>
                          <span className="text-[8px] font-bold opacity-30 uppercase">{f.desc}</span>
                        </div>
                      </button>
                    ))}
                  </div>
                </section>

                <section className="space-y-6 pt-6 border-t border-white/5">
                  <div className="flex items-center justify-between text-[11px] font-black uppercase tracking-widest text-white/30 px-1">
                    <span>Definição de Tempo</span>
                    <button onClick={addSegment} className="flex items-center gap-2 text-[#00f2ea] hover:scale-105 transition-all"><Plus size={16} /> Adicionar Corte</button>
                  </div>
                  <div className="space-y-3">
                    {segments.map((seg, idx) => (
                      <div key={idx} className="flex gap-6 items-center bg-white/[0.02] px-7 py-5 rounded-[1.5rem] border border-white/5 group hover:border-white/10 transition-all">
                        <Clock size={18} className="text-white/10" />
                        <div className="flex-1 grid grid-cols-2 gap-8">
                          <div className="flex flex-col">
                            <span className="text-[9px] font-black text-white/30 uppercase mb-2">Início (MM:SS)</span>
                            <input
                              type="text"
                              placeholder="00:00"
                              value={seg.start}
                              onChange={(e) => updateSegment(idx, 'start', formatTime(e.target.value))}
                              className="bg-transparent text-sm font-black focus:outline-none text-[#00f2ea] transition-all"
                            />
                          </div>
                          <div className="flex flex-col">
                            <span className="text-[9px] font-black text-white/30 uppercase mb-2">Fim (MM:SS)</span>
                            <input
                              type="text"
                              placeholder="00:30"
                              value={seg.end}
                              onChange={(e) => updateSegment(idx, 'end', formatTime(e.target.value))}
                              className="bg-transparent text-sm font-black focus:outline-none text-[#00f2ea] transition-all"
                            />
                          </div>
                        </div>
                        {segments.length > 1 && <button onClick={() => removeSegment(idx)} className="p-3 text-red-500/40 hover:text-red-500 transition-colors bg-white/5 rounded-xl"><Trash2 size={16} /></button>}
                      </div>
                    ))}
                  </div>
                </section>

                <section className="space-y-8 pt-6 border-t border-white/5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <MessageSquare size={18} className="text-[#00f2ea]" />
                      <label className="text-[12px] font-black text-white/40 uppercase tracking-[0.2em]">Legendas</label>
                    </div>
                    <div onClick={() => setSubtitlesActive(!subtitlesActive)} className={`w-12 h-6.5 rounded-full relative cursor-pointer transition-all duration-300 ${subtitlesActive ? 'bg-[#00f2ea]' : 'bg-white/10'}`}>
                      <div className={`w-4.5 h-4.5 bg-white rounded-full absolute top-1 transition-all ${subtitlesActive ? 'right-1 shadow-lg' : 'left-1'}`} />
                    </div>
                  </div>
                </section>

                {loading && (
                  <div className="p-8 bg-[#0d1117] border border-[#00f2ea]/10 rounded-[1.5rem] relative overflow-hidden">
                    <div className="absolute top-0 left-0 w-full h-1 bg-white/5">
                      <motion.div initial={{ left: '-100%' }} animate={{ left: '100%' }} transition={{ repeat: Infinity, duration: 1.5 }} className="w-1/2 h-full bg-[#00f2ea] shadow-[0_0_20px_#00f2ea]" />
                    </div>
                    <div className="flex flex-col gap-3">
                      {logs.map((log, i) => (
                        <div key={i} className="flex items-center gap-3">
                          <div className="w-1 h-1 bg-[#00f2ea] rounded-full" />
                          <span className={`text-[11px] font-bold uppercase tracking-widest ${i === logs.length - 1 ? 'text-white' : 'text-white/20'}`}>{log}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <button onClick={handleProcess} disabled={loading} className="w-full py-8 rounded-[2.2rem] bg-gradient-to-r from-[#00f2ea] to-[#00d8ff] text-[#0d1117] font-black uppercase tracking-[0.5em] shadow-[0_40px_80px_-20px_rgba(0,242,234,0.5)] disabled:opacity-20 transition-all active:scale-[0.98] group flex items-center justify-center gap-5 border-t border-white/30 sticky bottom-0 z-10">
                  {loading ? <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}><Settings size={32} /></motion.div> : <>Gerar Clips <Zap size={26} fill="#0d1117" /></>}
                </button>
              </>
            ) : (
              <div className="space-y-8 h-full min-h-[500px]">
                <div className="flex items-center justify-between">
                  <h3 className="text-xl font-black uppercase tracking-widest text-[#00f2ea]">Histórico</h3>
                  <button onClick={clearHistory} className="flex items-center gap-2 text-[10px] font-black text-red-500/50 hover:text-red-500 transition-colors uppercase"><Trash2 size={14} /> Limpar Tudo</button>
                </div>
                <div className="grid grid-cols-1 gap-4 overflow-y-auto max-h-[600px] custom-scrollbar pr-4">
                  {projects.length === 0 ? (
                    <div className="h-64 flex flex-col items-center justify-center text-center gap-6 opacity-20 border-2 border-dashed border-white/5 rounded-[2rem]">
                      <FileCode size={48} />
                      <span className="text-[12px] font-black uppercase tracking-widest">Nenhum projeto ainda</span>
                    </div>
                  ) : (
                    projects.map((p) => (
                      <div key={p.id} className="bg-white/5 border border-white/5 rounded-3xl p-6 flex flex-col gap-3 hover:bg-white/[0.08] transition-colors group">
                        <div className="flex items-center justify-between">
                          <span className="text-[12px] font-black uppercase tracking-tight text-white/80">{p.title}</span>
                          <span className="text-[9px] font-bold text-[#00f2ea] opacity-40 uppercase">{new Date(p.created_at).toLocaleDateString('pt-BR')}</span>
                        </div>
                        <div className="flex gap-4 items-center">
                          <div className="px-3 py-1 bg-[#00f2ea]/10 rounded-lg text-[9px] font-black text-[#00f2ea] uppercase border border-[#00f2ea]/20">
                            {p.clips_count || p.clips?.length || 0} Clips
                          </div>
                          <div className="ml-auto flex gap-3">
                            <button
                              onClick={(e) => { e.stopPropagation(); deleteProject(p.id); }}
                              className="p-2 text-red-500/40 hover:text-red-500 transition-colors bg-white/5 rounded-lg pointer-events-auto relative z-20"
                            >
                              <Trash2 size={14} />
                            </button>
                            <button
                              onClick={() => {
                                axios.get(`${API_BASE_URL}/videos/${p.id}`).then(res => {
                                  setResult(res.data);
                                  setActiveTab('config');
                                });
                              }}
                              className="p-2 bg-white text-black rounded-lg transition-transform hover:scale-110"
                            >
                              <ArrowRight size={14} />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

          <div className={`w-[580px] p-12 bg-black/40 flex flex-col transition-all duration-1000 border-l border-white/5 ${result ? 'bg-[#080b0f] translate-x-0' : 'opacity-0 translate-x-20 pointer-events-none'}`}>
            <AnimatePresence mode="wait">
              {result && (
                <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="w-full flex flex-col gap-12 h-full overflow-y-auto custom-scrollbar pr-2">
                  <div className="flex items-center justify-between">
                    <div className="flex flex-col">
                      <h3 className="text-2xl font-black italic uppercase text-white/95">CLIPS PRONTOS</h3>
                      <span className="text-[9px] text-[#00f2ea] font-black uppercase tracking-[0.2em] mt-1">{result.title}</span>
                    </div>
                    <button onClick={() => setResult(null)} className="p-3 hover:bg-white/5 rounded-2xl transition-all text-white/20 hover:text-white border border-white/5 font-black text-[15px]">×</button>
                  </div>

                  <div className={`relative group shrink-0 rounded-[4rem] border-[16px] border-[#252a31]/80 shadow-[0_80px_160px_-40px_rgba(0,0,0,1)] overflow-hidden bg-black mx-auto border-double transition-all duration-500 ${format === 'vertical' ? 'w-[300px] aspect-[9/16]' : format === 'square' ? 'w-[360px] aspect-square' : 'w-full aspect-[16/9]'}`}>
                    <video id="result-video" key={result.clips?.[selectedClipIndex]?.id || selectedClipIndex} src={`http://localhost:8001${result.clips?.[selectedClipIndex]?.video_path}`} controls className="w-full h-full object-cover" autoPlay />
                    <div className="absolute top-8 left-8 flex flex-col gap-2">
                      <div className="bg-black/60 backdrop-blur-md text-white text-[8px] font-black px-4 py-1.5 rounded-full uppercase tracking-widest border border-white/10">CLIP {selectedClipIndex + 1} DE {result.clips?.length}</div>
                    </div>
                  </div>

                  {result.clips?.length > 1 && (
                    <div className="flex justify-center gap-6 mt-[-20px] relative z-30">
                      <button onClick={() => setSelectedClipIndex(prev => Math.max(0, prev - 1))} className={`w-14 h-14 rounded-full bg-white/5 backdrop-blur-3xl border border-white/10 flex items-center justify-center hover:bg-[#00f2ea]/20 hover:border-[#00f2ea]/40 transition-all ${selectedClipIndex === 0 ? 'opacity-20 cursor-not-allowed' : 'opacity-100 hover:scale-110'}`}>
                        <ArrowLeft size={24} className="text-white" />
                      </button>
                      <button onClick={() => setSelectedClipIndex(prev => Math.min(result.clips.length - 1, prev + 1))} className={`w-14 h-14 rounded-full bg-white/5 backdrop-blur-3xl border border-white/10 flex items-center justify-center hover:bg-[#00f2ea]/20 hover:border-[#00f2ea]/40 transition-all ${selectedClipIndex === result.clips.length - 1 ? 'opacity-20 cursor-not-allowed' : 'opacity-100 hover:scale-110'}`}>
                        <ArrowRight size={24} className="text-white" />
                      </button>
                    </div>
                  )}

                  <div className="bg-[#1c2128]/80 rounded-[3rem] p-10 space-y-8 border border-white/5 backdrop-blur-3xl mx-2">
                    <button
                      onClick={async () => {
                        try {
                          const videoUrl = `http://localhost:8001${result.clips?.[selectedClipIndex]?.video_path}`;
                          const response = await fetch(videoUrl);
                          const blob = await response.blob();
                          const url = window.URL.createObjectURL(blob);
                          const link = document.createElement('a');
                          link.href = url;
                          link.setAttribute('download', `vimaclip_project_${result.id}_clip_${selectedClipIndex + 1}.mp4`);
                          document.body.appendChild(link);
                          link.click();
                          link.remove();
                          window.URL.revokeObjectURL(url);
                        } catch (err) {
                          console.error("Erro no download:", err);
                          alert("Erro ao baixar o vídeo. Tente novamente.");
                        }
                      }}
                      className="w-full flex items-center justify-center gap-5 bg-white text-[#0d1117] py-7 rounded-[28px] text-[14px] font-black uppercase tracking-[0.3em] hover:bg-[#00f2ea] transition-all shadow-xl shadow-white/5 active:scale-95"
                    >
                      <Download size={24} /> Baixar Clip
                    </button>
                    <div className="pt-6 border-t border-white/5 flex flex-col gap-5">
                      <div className="flex gap-4">
                        <button onClick={() => setShowTranscription(!showTranscription)} className={`flex-1 py-4 border border-white/5 rounded-2xl text-[9px] font-black uppercase transition-all ${showTranscription ? 'bg-[#00f2ea] text-black' : 'bg-white/[0.03] text-white/30'}`}>Ver Transcrição</button>
                        <button className="flex-1 py-4 bg-white/[0.03] border border-white/5 rounded-2xl text-[9px] font-black uppercase text-white/30 hover:text-white transition-all">Exportar SRT</button>
                      </div>
                      {showTranscription && result.clips?.[selectedClipIndex]?.transcription && (
                        <div className="p-6 bg-black/40 rounded-[2rem] border border-white/5 max-h-[150px] overflow-y-auto custom-scrollbar">
                          <p className="text-[11px] text-white/60 leading-relaxed">{result.clips[selectedClipIndex].transcription.text}</p>
                          <button onClick={() => { navigator.clipboard.writeText(result.clips[selectedClipIndex].transcription.text); alert("Copiado!"); }} className="mt-4 text-[9px] font-black text-[#00f2ea] uppercase tracking-widest">Copiar Texto</button>
                        </div>
                      )}
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </motion.div>

      <AnimatePresence>
        {error && (
          <motion.div initial={{ opacity: 0, y: 50 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 50 }} className="fixed bottom-12 left-1/2 -translate-x-1/2 bg-red-600/95 backdrop-blur-2xl text-white px-10 py-7 rounded-[2.5rem] shadow-2xl flex items-center gap-7 z-[100] border border-white/20 min-w-[500px]">
            <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center shrink-0"><AlertCircle size={28} /></div>
            <div className="flex flex-col flex-1">
              <span className="text-[10px] font-black uppercase opacity-50">Erro</span>
              <span className="text-[14px] font-bold">{error}</span>
            </div>
            <button onClick={() => setError(null)} className="text-white/50 text-2xl">×</button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default App;
