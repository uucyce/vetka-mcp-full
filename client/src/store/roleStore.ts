/**
 * useRoleStore - Zustand store for custom agent roles with persistence.
 * Manages role CRUD, import/export, and localStorage sync.
 *
 * @status active
 * @phase 96
 * @depends zustand, zustand/middleware (persist), immer
 * @used_by RoleEditor, MentionPopup
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { produce } from 'immer';

export interface CustomRole {
  id: string;
  name: string; // "@architect"
  displayName: string; // "Senior Architect"
  systemPrompt: string; // Full system message
  capabilities: string[]; // ["code", "design"]
  preferredModel?: string;
  createdAt: Date;
  updatedAt: Date;
}

interface RoleStore {
  roles: CustomRole[];
  addRole: (role: Omit<CustomRole, 'id' | 'createdAt' | 'updatedAt'>) => void;
  updateRole: (id: string, updates: Partial<CustomRole>) => void;
  deleteRole: (id: string) => void;
  exportRole: (id: string) => void;
  importRole: (json: string) => void;
  getRoleById: (id: string) => CustomRole | undefined;
}

export const useRoleStore = create<RoleStore>()(
  persist(
    (set, get) => ({
      roles: [],

      addRole: (roleData) => {
        const newRole: CustomRole = {
          ...roleData,
          id: `role-${crypto.randomUUID()}`,
          createdAt: new Date(),
          updatedAt: new Date(),
        };

        set(
          produce((state) => {
            state.roles.push(newRole);
          })
        );

        // Sync to backend (async, non-blocking)
        fetch('/api/roles', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(newRole),
        }).catch(console.error);
      },

      updateRole: (id, updates) => {
        set(
          produce((state) => {
            const role = state.roles.find((r: CustomRole) => r.id === id);
            if (role) {
              Object.assign(role, updates, { updatedAt: new Date() });
            }
          })
        );
      },

      deleteRole: (id) => {
        set(
          produce((state) => {
            state.roles = state.roles.filter((r: CustomRole) => r.id !== id);
          })
        );
      },

      exportRole: (id) => {
        const role = get().roles.find((r) => r.id === id);
        if (!role) return;

        const blob = new Blob([JSON.stringify(role, null, 2)], {
          type: 'application/json',
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${role.name}.vetka-role.json`;
        a.click();
        URL.revokeObjectURL(url);
      },

      importRole: (json) => {
        try {
          const parsed = JSON.parse(json);
          if (!parsed.name || !parsed.systemPrompt) {
            throw new Error('Invalid role format');
          }
          get().addRole(parsed);
        } catch (err) {
          console.error('Import failed:', err);
        }
      },

      getRoleById: (id) => {
        const state = get();
        return state.roles.find((r) => r.id === id);
      },
    }),
    {
      name: 'vetka-custom-roles',
      version: 1,
    }
  )
);
