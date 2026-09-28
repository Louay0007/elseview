import { GripVertical, Pencil, Plus, Search, Trash2 } from "lucide-react";
import { type BuilderProps } from "./types";

type TreeNode = { id: string; label: string; parentId?: string };

const starterNodes: TreeNode[] = [
  { id: "home", label: "Home" },
];

export function TreeTestBuilder({ text, custom, onPatch }: BuilderProps) {
  const nodes = (custom.tree_nodes as TreeNode[]) ?? starterNodes;
  const tasks = (custom.tree_tasks as string[]) ?? [];
  const search = (custom.tree_search as string) ?? "";

  const updateNodes = (next: TreeNode[]) => onPatch({ tree_nodes: next });
  const childrenOf = (parentId?: string) => nodes.filter((node) => node.parentId === parentId);
  const addNode = (parentId?: string) => updateNodes([...nodes, { id: `node-${Date.now()}`, label: "", parentId }]);
  const updateNode = (id: string, label: string) => updateNodes(nodes.map((node) => node.id === id ? { ...node, label } : node));
  const removeNode = (id: string) => updateNodes(nodes.filter((node) => node.id !== id && node.parentId !== id));

  const renderNodes = (parentId?: string, depth = 0) => childrenOf(parentId)
    .filter((node) => !search.trim() || node.label.toLowerCase().includes(search.toLowerCase()))
    .map((node) => (
      <div key={node.id} className="relative" style={{ marginLeft: depth ? `${depth * 20}px` : undefined }}>
        {depth > 0 && <span className="absolute -left-3 top-0 h-5 w-3 border-b border-l border-[#a1a1aa]" aria-hidden="true" />}
        <div className="mb-2 flex min-h-[38px] items-center gap-2 rounded-md bg-[#ead5ff] px-3 text-[12.5px] text-[#0b1e4b]">
          <GripVertical className="size-3.5 text-[#7c3aed]" aria-hidden="true" />
          <input value={node.label} onChange={(event) => updateNode(node.id, event.target.value)} placeholder={text({ en: "Node name", fr: "Nom du noeud" })} className="min-w-0 flex-1 bg-transparent text-[12.5px] font-medium outline-none placeholder:text-[#805e9e]" />
          <button type="button" onClick={() => addNode(node.id)} className="inline-flex items-center gap-1 text-[11px] font-medium hover:underline"><Plus className="size-3" />{text({ en: "Add child", fr: "Ajouter enfant" })}</button>
          <button type="button" className="grid size-5 place-items-center hover:text-[#1d4ed8]" aria-label={text({ en: "Edit node", fr: "Modifier" })}><Pencil className="size-3" /></button>
          {node.id !== "home" && <button type="button" onClick={() => removeNode(node.id)} className="grid size-5 place-items-center hover:text-[#b42318]" aria-label={text({ en: "Remove node", fr: "Supprimer" })}><Trash2 className="size-3" /></button>}
        </div>
        {renderNodes(node.id, depth + 1)}
      </div>
    ));

  return (
    <div className="grid min-w-0 gap-6">
      <section className="rounded-2xl border border-[#e8e8ec] bg-white p-5">
        <p className="text-[14px] font-bold text-[#0b1e4b]">{text({ en: "Creating the tree", fr: "Créer l’arborescence" })}</p>
        <p className="mt-1 max-w-[70ch] text-[12.5px] leading-relaxed text-[#6d6d70]">{text({ en: "Your Tree is a text-only version of your website hierarchy. Your category labels (first level, second level, etc.) are called “nodes”, and subcategories are known as “child nodes”.", fr: "Votre arbre est une version textuelle de la hiérarchie de votre site." })}</p>
        <p className="mt-2 text-[12.5px] text-[#6d6d70]">{text({ en: "You can also import a CSV file to automatically create your tree.", fr: "Vous pouvez aussi importer un fichier CSV pour créer votre arbre." })} <button type="button" className="text-[#1d4ed8] hover:underline">{text({ en: "Download CSV template", fr: "Télécharger le modèle CSV" })}</button></p>

        <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
          <p className="text-[13px] font-bold text-[#0b1e4b]">{text({ en: "Build the tree", fr: "Construire l’arbre" })} <span className="ml-1 rounded-full border border-[#d9d9df] px-2 py-1 text-[10px] font-medium">{text({ en: "max 2", fr: "max 2" })}</span></p>
          <label className="relative block w-full sm:w-72"><Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-[#6d6d70]" aria-hidden="true" /><input value={search} onChange={(event) => onPatch({ tree_search: event.target.value })} placeholder={text({ en: "Search for node or child", fr: "Rechercher un noeud" })} className="min-h-[38px] w-full rounded-lg border border-[#d9d9df] py-2 pl-9 pr-3 text-[12.5px] outline-none placeholder:text-[#a1a1aa] focus:border-[#1d4ed8] focus:ring-2 focus:ring-[#1d4ed8]/20" /></label>
        </div>

        <div className="mt-4 min-h-[220px] rounded-lg border border-[#f0f0f3] bg-[#fcfcfd] p-3">{renderNodes()}</div>
        <button type="button" onClick={() => addNode()} className="mt-4 inline-flex min-h-[36px] items-center gap-1.5 rounded-full bg-[#18181b] px-4 text-[13px] font-medium text-white hover:bg-black"><Plus className="size-4" aria-hidden="true" />{text({ en: "Add node", fr: "Ajouter un noeud" })}</button>
        <div className="mt-4 flex items-center gap-4 text-[11.5px]"><span className="text-[#7c3aed]">{nodes.length} {text({ en: "nodes", fr: "noeuds" })}</span><button type="button" onClick={() => updateNodes(starterNodes)} className="inline-flex items-center gap-1 text-[#52525b] hover:text-[#b42318]">{text({ en: "Delete all", fr: "Tout supprimer" })}<Trash2 className="size-3" /></button></div>
      </section>

      <section className="rounded-2xl border border-[#e8e8ec] bg-white p-5">
        <p className="text-[14px] font-bold text-[#0b1e4b]">{text({ en: "Tasks", fr: "Tâches" })}</p>
        <p className="mt-1 max-w-[70ch] text-[12.5px] leading-relaxed text-[#6d6d70]">{text({ en: "Your tasks should reflect how your participants naturally approach your website and be linked to your testing objectives.", fr: "Vos tâches doivent refléter la façon dont les participants explorent naturellement votre site." })}</p>
        <p className="mt-2 text-[12.5px] text-[#6d6d70]">{text({ en: "Tip: Use a hypothetical scenario. For example: “If you’re hosting a dinner party, where would you find glassware?”", fr: "Conseil : utilisez un scénario hypothétique." })}</p>
        <div className="mt-4 space-y-2">{tasks.map((task, index) => <input key={index} value={task} onChange={(event) => onPatch({ tree_tasks: tasks.map((value, itemIndex) => itemIndex === index ? event.target.value : value) })} placeholder={text({ en: "Task", fr: "Tâche" })} className="min-h-[42px] w-full rounded-lg border border-[#d9d9df] px-3 text-[13px] outline-none focus:border-[#1d4ed8]" />)}</div>
        <button type="button" onClick={() => onPatch({ tree_tasks: [...tasks, ""] })} className="mt-4 inline-flex min-h-[36px] items-center gap-1.5 rounded-full border border-[#18181b] px-4 text-[13px] font-medium text-[#18181b] hover:bg-[#f7f8fa]"><Plus className="size-4" />{text({ en: "Add task", fr: "Ajouter une tâche" })}</button>
      </section>
    </div>
  );
}
