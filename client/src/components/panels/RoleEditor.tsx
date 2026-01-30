/**
 * RoleEditor - Modal for creating and editing custom agent roles.
 * Manages role ID, display name, system prompt, and capabilities.
 *
 * @status active
 * @phase 96
 * @depends react, useRoleStore, framer-motion, lucide-react
 * @used_by App (via modal system)
 */

import { useState } from 'react';
import { useRoleStore, CustomRole } from '../../store/roleStore';
import { motion } from 'framer-motion';
import { X } from 'lucide-react';

interface RoleEditorProps {
  role?: CustomRole;
  onSave: () => void;
  onCancel: () => void;
}

export const RoleEditor = ({ role, onSave, onCancel }: RoleEditorProps) => {
  const addRole = useRoleStore((s) => s.addRole);
  const updateRole = useRoleStore((s) => s.updateRole);

  const [name, setName] = useState(role?.name || '@');
  const [displayName, setDisplayName] = useState(role?.displayName || '');
  const [systemPrompt, setSystemPrompt] = useState(role?.systemPrompt || '');
  const [capabilities, setCapabilities] = useState<string[]>(role?.capabilities || []);
  const [preferredModel, setPreferredModel] = useState(role?.preferredModel || '');

  const [errors, setErrors] = useState<Record<string, string>>({});

  const CAPABILITY_OPTIONS = ['code', 'design', 'review', 'test', 'document', 'research'];

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!name.trim() || !name.startsWith('@')) {
      newErrors.name = 'Role ID must start with @';
    }
    if (!displayName.trim()) {
      newErrors.displayName = 'Display name is required';
    }
    if (!systemPrompt.trim()) {
      newErrors.systemPrompt = 'System prompt is required';
    }
    if (systemPrompt.length < 50) {
      newErrors.systemPrompt = 'System prompt should be at least 50 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = () => {
    if (!validateForm()) return;

    const roleData = {
      name,
      displayName,
      systemPrompt,
      capabilities,
      preferredModel: preferredModel || undefined,
    };

    if (role) {
      updateRole(role.id, roleData);
    } else {
      addRole(roleData);
    }

    onSave();
  };

  const toggleCapability = (cap: string) => {
    setCapabilities((prev) =>
      prev.includes(cap) ? prev.filter((c) => c !== cap) : [...prev, cap]
    );
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/80 z-60 flex items-center justify-center p-4"
    >
      <motion.div
        initial={{ scale: 0.95, y: 20 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.95, y: 20 }}
        className="bg-gray-900 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto border border-gray-700"
      >
        <div className="p-6 space-y-4">
          {/* Header */}
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-white">
              {role ? 'Edit Role' : 'Create New Role'}
            </h2>
            <button
              onClick={onCancel}
              className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
            >
              <X size={20} className="text-gray-400" />
            </button>
          </div>

          {/* Name */}
          <div>
            <label className="text-sm text-gray-400 block mb-1">Role ID (e.g., @architect)</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className={`w-full p-2 bg-gray-800 border rounded text-white placeholder-gray-500 focus:outline-none transition-colors ${
                errors.name ? 'border-red-500 focus:border-red-500' : 'border-gray-700 focus:border-blue-500'
              }`}
              placeholder="@my_role"
            />
            {errors.name && <p className="text-xs text-red-400 mt-1">{errors.name}</p>}
          </div>

          {/* Display Name */}
          <div>
            <label className="text-sm text-gray-400 block mb-1">Display Name</label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className={`w-full p-2 bg-gray-800 border rounded text-white placeholder-gray-500 focus:outline-none transition-colors ${
                errors.displayName ? 'border-red-500 focus:border-red-500' : 'border-gray-700 focus:border-blue-500'
              }`}
              placeholder="Senior Architect"
            />
            {errors.displayName && (
              <p className="text-xs text-red-400 mt-1">{errors.displayName}</p>
            )}
          </div>

          {/* System Prompt */}
          <div>
            <label className="text-sm text-gray-400 block mb-1">System Prompt</label>
            <textarea
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              rows={10}
              className={`w-full p-3 bg-gray-800 border rounded font-mono text-sm text-white placeholder-gray-500 focus:outline-none transition-colors ${
                errors.systemPrompt ? 'border-red-500 focus:border-red-500' : 'border-gray-700 focus:border-blue-500'
              }`}
              placeholder="You are a senior architect specialized in..."
            />
            <div className="flex items-center justify-between mt-1">
              <p className="text-xs text-gray-500">{systemPrompt.length} characters</p>
              {errors.systemPrompt && (
                <p className="text-xs text-red-400">{errors.systemPrompt}</p>
              )}
            </div>
          </div>

          {/* Preferred Model */}
          <div>
            <label className="text-sm text-gray-400 block mb-1">Preferred Model (optional)</label>
            <select
              value={preferredModel}
              onChange={(e) => setPreferredModel(e.target.value)}
              className="w-full p-2 bg-gray-800 border border-gray-700 rounded text-white focus:border-blue-500 focus:outline-none transition-colors"
            >
              <option value="">Auto-select</option>
              <option value="gpt-4">GPT-4</option>
              <option value="gpt-4-vision">GPT-4 Vision</option>
              <option value="claude-3">Claude 3</option>
              <option value="claude-vision">Claude Vision</option>
            </select>
          </div>

          {/* Capabilities */}
          <div>
            <label className="text-sm text-gray-400 block mb-2">Capabilities</label>
            <div className="flex flex-wrap gap-2">
              {CAPABILITY_OPTIONS.map((cap) => (
                <motion.button
                  key={cap}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => toggleCapability(cap)}
                  className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                    capabilities.includes(cap)
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                  }`}
                >
                  {cap}
                </motion.button>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-4 border-t border-gray-700">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={onCancel}
              className="flex-1 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg transition-colors"
            >
              Cancel
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleSave}
              disabled={!name || !displayName || !systemPrompt}
              className="flex-1 py-2 bg-green-600 hover:bg-green-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg transition-colors font-medium"
            >
              {role ? 'Update Role' : 'Create Role'}
            </motion.button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
};
