import React, { useState, useEffect } from 'react';
import { Plus, Trash2, Link as LinkIcon, AlertCircle, Save, Loader } from 'lucide-react';
const API_BASE_URL = 'http://localhost:8000';

const ManageSourcesPage = () => {
  const [goldTargets, setGoldTargets] = useState([]);
  const [houseTargets, setHouseTargets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [newTarget, setNewTarget] = useState({ type: 'gold', url: '' });
  const [adding, setAdding] = useState(false);

  const fetchData = async () => {
    try {
      setLoading(true);
      const resGold = await fetch(`${API_BASE_URL}/api/targets/gold`);
      const resHouse = await fetch(`${API_BASE_URL}/api/targets/real_estate`);
      setGoldTargets(await resGold.json());
      setHouseTargets(await resHouse.json());
      setError(null);
    } catch (err) {
      console.error(err);
      setError('Failed to load sources configuration.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleDelete = async (type, id) => {
    if (!window.confirm(`Are you sure you want to delete source: ${id}?`)) return;
    try {
      await fetch(`${API_BASE_URL}/api/targets/${type}/${id}`, { method: 'DELETE' });
      fetchData();
    } catch (err) {
      console.error(err);
      alert('Failed to delete source.');
    }
  };

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!newTarget.url) return;
    setAdding(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/targets/${newTarget.type}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: newTarget.url
        })
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Failed to add source');
      }
      setNewTarget({ ...newTarget, url: '' });
      fetchData();
    } catch (err) {
      console.error(err);
      alert(err.message || 'Failed to add source.');
    } finally {
      setAdding(false);
    }
  };

  const TargetTable = ({ title, type, data, icon: Icon, color }) => (
    <div className="bg-slate-800/50 backdrop-blur-md rounded-xl p-6 border border-slate-700/50 flex flex-col h-full shadow-lg">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg bg-${color}-500/20 text-${color}-400`}>
            <Icon className="w-5 h-5" />
          </div>
          <h2 className="text-xl font-bold text-white">{title}</h2>
        </div>
        <span className="px-3 py-1 bg-slate-700/50 text-slate-300 rounded-full text-sm font-medium border border-slate-600/50">
          {data.length} Sources
        </span>
      </div>

      <div className="flex-grow overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-700/50 text-slate-400 text-sm">
              <th className="pb-3 font-semibold px-2">ID</th>
              <th className="pb-3 font-semibold px-2">Target URL</th>
              <th className="pb-3 font-semibold text-right px-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {data.length === 0 ? (
              <tr>
                <td colSpan="3" className="py-8 text-center text-slate-500">
                  No sources configured.
                </td>
              </tr>
            ) : (
              data.map((item) => (
                <tr key={item.id} className="border-b border-slate-700/50 hover:bg-slate-700/20 transition-colors">
                  <td className="py-4 px-2 font-medium text-slate-200">
                    <span className="px-2 py-1 bg-slate-900/50 rounded text-xs border border-slate-700 text-slate-300 font-mono">
                      {item.id}
                    </span>
                  </td>
                  <td className="py-4 px-2">
                    <a 
                      href={item.url} 
                      target="_blank" 
                      rel="noreferrer"
                      className="text-blue-400 hover:text-blue-300 hover:underline flex items-center gap-2 truncate max-w-[250px]"
                      title={item.url}
                    >
                      {item.url}
                    </a>
                  </td>
                  <td className="py-4 px-2 text-right">
                    <button 
                      onClick={() => handleDelete(type, item.id)}
                      className="p-2 text-slate-400 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-colors"
                      title="Delete Source"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">Crawl Orchestrator</h1>
        <p className="text-slate-400 max-w-2xl text-lg">
          Manage dynamic target URLs for the background data collection engine. Changes take effect immediately on the next background fetch.
        </p>
      </header>

      {error && (
        <div className="bg-red-500/10 border border-red-500/50 text-red-400 p-4 rounded-xl flex items-center gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {/* Add New Source Form */}
      <div className="bg-gradient-to-br from-indigo-900/40 to-purple-900/40 backdrop-blur-md rounded-xl p-6 border border-indigo-500/30 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 p-32 bg-purple-500/10 rounded-full blur-3xl -mr-16 -mt-16 pointer-events-none"></div>
        
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 rounded-lg bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
            <Plus className="w-5 h-5" />
          </div>
          <h2 className="text-xl font-bold text-white">Add Target Source</h2>
        </div>

        <form onSubmit={handleAdd} className="grid grid-cols-1 md:grid-cols-12 gap-4 items-end relative z-10">
          <div className="md:col-span-3">
            <label className="block text-sm font-medium text-slate-300 mb-2">Category</label>
            <select
              value={newTarget.type}
              onChange={(e) => setNewTarget({ ...newTarget, type: e.target.value })}
              className="w-full bg-slate-900/80 border border-slate-700 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-indigo-500 transition-colors"
            >
              <option value="gold">Gold Price</option>
              <option value="real_estate">Real Estate</option>
            </select>
          </div>
          
          <div className="md:col-span-7">
            <label className="block text-sm font-medium text-slate-300 mb-2">Target URL</label>
            <div className="relative">
              <LinkIcon className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="url"
                placeholder="https://example.com/prices"
                value={newTarget.url}
                onChange={(e) => setNewTarget({ ...newTarget, url: e.target.value })}
                className="w-full bg-slate-900/80 border border-slate-700 rounded-lg pl-10 pr-4 py-2.5 text-white focus:outline-none focus:border-indigo-500 transition-colors placeholder:text-slate-600"
                required
              />
            </div>
          </div>

          <div className="md:col-span-2">
            <button
              type="submit"
              disabled={adding}
              className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-medium py-2.5 px-4 rounded-lg transition-colors flex items-center justify-center gap-2 border border-indigo-400/50 shadow-lg shadow-indigo-900/20 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {adding ? <Loader className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              Save Source
            </button>
          </div>
        </form>
      </div>

      {loading ? (
        <div className="flex justify-center items-center py-20">
          <Loader className="w-8 h-8 text-indigo-500 animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <TargetTable 
            title="Gold Targets" 
            type="gold" 
            data={goldTargets} 
            icon={LinkIcon} 
            color="yellow" 
          />
          <TargetTable 
            title="Real Estate Targets" 
            type="real_estate" 
            data={houseTargets} 
            icon={LinkIcon} 
            color="blue" 
          />
        </div>
      )}
    </div>
  );
};

export default ManageSourcesPage;
