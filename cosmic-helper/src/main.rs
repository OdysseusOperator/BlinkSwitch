use std::collections::HashMap;
use std::io::{self, BufRead, Write};

use cosmic_client_toolkit::sctk::registry::{ProvidesRegistryState, RegistryHandler, RegistryState};
use cosmic_client_toolkit::toplevel_info::{ToplevelInfoHandler, ToplevelInfoState};
use cosmic_client_toolkit::toplevel_management::{ToplevelManagerHandler, ToplevelManagerState};
use cosmic_client_toolkit::workspace::{WorkspaceHandler, WorkspaceState};
use cosmic_client_toolkit::{delegate_toplevel_info, delegate_toplevel_manager, delegate_workspace};
use cosmic_client_toolkit::cosmic_protocols::toplevel_management::v1::client::zcosmic_toplevel_manager_v1::ZcosmicToplelevelManagementCapabilitiesV1 as Capability;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use smithay_client_toolkit::reexports::client::globals::{registry_queue_init, GlobalList};
use smithay_client_toolkit::reexports::client::protocol::{wl_output, wl_seat};
use smithay_client_toolkit::reexports::client::{Connection, Dispatch, Proxy, QueueHandle, WEnum};
use smithay_client_toolkit::{delegate_registry, registry_handlers};
use wayland_protocols::ext::foreign_toplevel_list::v1::client::ext_foreign_toplevel_handle_v1::ExtForeignToplevelHandleV1;

#[derive(Clone, Debug, Default)]
struct OutputData {
    name: Option<String>,
    description: Option<String>,
    make: Option<String>,
    model: Option<String>,
    x: i32,
    y: i32,
    width: i32,
    height: i32,
    scale: i32,
    refresh_millihz: i32,
}

#[derive(Debug, Deserialize)]
struct Command {
    #[serde(alias = "op")]
    command: String,
    id: Option<i64>,
    #[serde(alias = "target_output")]
    output: Option<String>,
    workspace: Option<String>,
}

#[derive(Debug, Serialize)]
struct Reply {
    ok: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    error: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    result: Option<Value>,
}

struct App {
    connection: Connection,
    registry_state: RegistryState,
    toplevel_info: ToplevelInfoState,
    toplevel_manager: ToplevelManagerState,
    workspace: WorkspaceState,
    outputs: Vec<wl_output::WlOutput>,
    output_data: HashMap<u32, OutputData>,
    seat: Option<wl_seat::WlSeat>,
    // Proxy IDs remain stable for the lifetime of this persistent helper.
    ids: HashMap<u32, i64>,
    next_id: i64,
    capabilities: Vec<WEnum<Capability>>,
}

impl App {
    fn new(connection: &Connection, globals: GlobalList, qh: &QueueHandle<Self>) -> Self {
        let registry_state = RegistryState::new(&globals);
        let outputs = registry_state
            .bind_all(qh, 1..=4, |_global_name| {
                OutputData { ..Default::default() }
            })
            .unwrap_or_default();
        let seat = registry_state.bind_one(qh, 1..=9, ()).ok();
        let toplevel_info = ToplevelInfoState::new(&registry_state, qh);
        let toplevel_manager = ToplevelManagerState::new(&registry_state, qh);
        let workspace = WorkspaceState::new(&registry_state, qh);
        let app = Self {
            connection: connection.clone(),
            registry_state,
            toplevel_info,
            toplevel_manager,
            workspace,
            outputs,
            output_data: HashMap::new(),
            seat,
            ids: HashMap::new(),
            next_id: 1,
            capabilities: Vec::new(),
        };
        let _ = connection.flush();
        app
    }

    fn id_for(&mut self, key: u32) -> i64 {
        if let Some(id) = self.ids.get(&key) {
            return *id;
        }
        let id = self.next_id;
        self.next_id += 1;
        self.ids.insert(key, id);
        id
    }

    fn output(&self, requested: Option<&str>) -> Option<wl_output::WlOutput> {
        self.outputs.iter().find_map(|output| {
            let data = self.output_data.get(&output.id().protocol_id())?;
            match requested {
                None => Some(output.clone()),
                Some(value) if data.name.as_deref() == Some(value) => Some(output.clone()),
                Some(value) if data.description.as_deref() == Some(value) => Some(output.clone()),
                _ => None,
            }
        })
    }

    fn handle(&mut self, command: Command) -> Reply {
        let result = match command.command.as_str() {
            "list" | "list_windows" => Ok(self.list()),
            "focus" | "fullscreen" | "unfullscreen" | "maximize" | "unmaximize" => self.action(&command.command, command.id, command.output),
            "move_workspace" => self.move_workspace(command.id, command.workspace, command.output),
            _ => Err(format!("unknown command: {}", command.command)),
        };
        match result {
            Ok(value) => Reply { ok: true, error: None, result: Some(value) },
            Err(error) => Reply { ok: false, error: Some(error), result: None },
        }
    }

    fn action(&mut self, command: &str, id: Option<i64>, output_name: Option<String>) -> Result<Value, String> {
        let id = id.ok_or("missing id".to_string())?;
        let handle = self.find_info(id).and_then(|info| info.cosmic_toplevel.clone()).ok_or("unknown id or COSMIC handle unavailable".to_string())?;
        match command {
            "focus" => {
                let seat = self.seat.clone().ok_or("no wl_seat global".to_string())?;
                self.toplevel_manager.manager.activate(&handle, &seat);
            }
            "fullscreen" => self.toplevel_manager.manager.set_fullscreen(&handle, self.output(output_name.as_deref()).as_ref()),
            "unfullscreen" => self.toplevel_manager.manager.unset_fullscreen(&handle),
            "maximize" => self.toplevel_manager.manager.set_maximized(&handle),
            "unmaximize" => self.toplevel_manager.manager.unset_maximized(&handle),
            _ => return Err("unsupported action".to_string()),
        }
        self.flush();
        Ok(json!({"id": id, "requested": true}))
    }

    fn find_info(&self, id: i64) -> Option<&cosmic_client_toolkit::toplevel_info::ToplevelInfo> {
        self.toplevel_info.toplevels().find(|info| {
            self.ids.get(&info.foreign_toplevel.id().protocol_id()).copied() == Some(id)
        })
    }

    fn move_workspace(&mut self, id: Option<i64>, workspace: Option<String>, output: Option<String>) -> Result<Value, String> {
        let id = id.ok_or("missing id".to_string())?;
        let info = self.find_info(id).ok_or("unknown id".to_string())?;
        let handle = info.cosmic_toplevel.clone().ok_or("COSMIC handle unavailable".to_string())?;
        let output = self.output(output.as_deref()).ok_or("target output not found".to_string())?;
        let workspace = workspace.ok_or("missing workspace".to_string())?;
        let target = self.workspace.workspaces().find(|item| item.id.as_deref() == Some(&workspace) || item.name == workspace).ok_or("target workspace not found".to_string())?.handle.clone();
        self.toplevel_manager.manager.move_to_ext_workspace(&handle, &target, &output);
        self.flush();
        Ok(json!({"id": id, "requested": true, "workspace": workspace}))
    }

    fn list(&mut self) -> Value {
        let infos: Vec<_> = self.toplevel_info.toplevels().cloned().collect();
        let windows: Vec<Value> = infos.iter().map(|info| {
            let id = self.id_for(info.foreign_toplevel.id().protocol_id());
            let states: Vec<String> = info.state.iter().map(|state| format!("{state:?}").to_lowercase()).collect();
            let outputs: Vec<Value> = info.output.iter().map(|output| self.output_json(output)).collect();
            let workspaces: Vec<Value> = info.workspace.iter().map(|workspace| {
                self.workspace.workspaces().find(|item| item.handle == *workspace).map(|item| json!({"id": item.id, "name": item.name, "coordinates": item.coordinates}))
            }).flatten().collect();
            json!({"id": id, "title": info.title, "app_id": info.app_id, "identifier": info.identifier, "states": states, "outputs": outputs, "workspaces": workspaces, "geometry": info.geometry.iter().map(|(output, geometry)| json!({"output_id": output.id().protocol_id(), "output": self.output_data.get(&output.id().protocol_id()).and_then(|data| data.name.clone()), "x": geometry.x, "y": geometry.y, "width": geometry.width, "height": geometry.height})).collect::<Vec<_>>()})
        }).collect();
        let outputs: Vec<Value> = self.outputs.iter().map(|output| {
            self.output_json(output)
        }).collect();
        json!({"windows": windows, "outputs": outputs, "workspaces": self.workspace.workspaces().map(|item| {
            let output_ids: Vec<u32> = self.workspace.workspace_groups()
                .filter(|group| group.workspaces.contains(&item.handle))
                .flat_map(|group| group.outputs.iter().map(|output| output.id().protocol_id()))
                .collect();
            json!({"id": item.id, "name": item.name, "coordinates": item.coordinates, "output_ids": output_ids, "state": format!("{:?}", item.state).to_lowercase(), "cosmic_state": format!("{:?}", item.cosmic_state).to_lowercase()})
        }).collect::<Vec<_>>(), "capabilities": self.capabilities.iter().map(|cap| format!("{cap:?}").to_lowercase()).collect::<Vec<_>>()})
    }

    fn output_json(&self, output: &wl_output::WlOutput) -> Value {
        let data = self.output_data.get(&output.id().protocol_id()).cloned().unwrap_or_default();
        json!({"id": output.id().protocol_id(), "name": data.name, "description": data.description, "make": data.make, "model": data.model, "x": data.x, "y": data.y, "width": data.width, "height": data.height, "scale": data.scale, "refresh_millihz": data.refresh_millihz})
    }

    fn flush(&self) { let _ = self.connection.flush(); }
}

impl ProvidesRegistryState for App {
    fn registry(&mut self) -> &mut RegistryState { &mut self.registry_state }
    registry_handlers!(App);
}
impl RegistryHandler<App> for App {}
impl ToplevelInfoHandler for App {
    fn toplevel_info_state(&mut self) -> &mut ToplevelInfoState { &mut self.toplevel_info }
    fn new_toplevel(&mut self, _: &Connection, _: &QueueHandle<Self>, _: &ExtForeignToplevelHandleV1) {}
    fn update_toplevel(&mut self, _: &Connection, _: &QueueHandle<Self>, _: &ExtForeignToplevelHandleV1) {}
    fn toplevel_closed(&mut self, _: &Connection, _: &QueueHandle<Self>, _: &ExtForeignToplevelHandleV1) {}
}
impl WorkspaceHandler for App { fn workspace_state(&mut self) -> &mut WorkspaceState { &mut self.workspace } fn done(&mut self) {} }
impl ToplevelManagerHandler for App {
    fn toplevel_manager_state(&mut self) -> &mut ToplevelManagerState { &mut self.toplevel_manager }
    fn capabilities(&mut self, _: &Connection, _: &QueueHandle<Self>, capabilities: Vec<WEnum<Capability>>) { self.capabilities = capabilities; }
}

impl Dispatch<wl_output::WlOutput, OutputData> for App {
    fn event(state: &mut Self, output: &wl_output::WlOutput, event: wl_output::Event, _: &OutputData, _: &Connection, _: &QueueHandle<Self>) {
        let data = state.output_data.entry(output.id().protocol_id()).or_default();
        match event {
            wl_output::Event::Name { name } => data.name = Some(name),
            wl_output::Event::Description { description } => data.description = Some(description),
            wl_output::Event::Geometry { x, y, make, model, .. } => { data.x = x; data.y = y; data.make = Some(make); data.model = Some(model); }
            wl_output::Event::Mode { width, height, refresh, flags } if matches!(flags, WEnum::Value(flags) if flags.contains(wl_output::Mode::Current)) => { data.width = width; data.height = height; data.refresh_millihz = refresh; }
            wl_output::Event::Scale { factor } => data.scale = factor,
            _ => {}
        }
    }
}
impl Dispatch<wl_seat::WlSeat, ()> for App {
    fn event(_: &mut Self, _: &wl_seat::WlSeat, _: wl_seat::Event, _: &(), _: &Connection, _: &QueueHandle<Self>) {}
}

delegate_registry!(App);
delegate_toplevel_info!(App);
delegate_toplevel_manager!(App);
delegate_workspace!(App);

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let connection = Connection::connect_to_env()?;
    let (globals, mut event_queue) = registry_queue_init(&connection)?;
    let qh = event_queue.handle();
    let mut app = App::new(&connection, globals, &qh);
    event_queue.roundtrip(&mut app)?;
    let stdin = io::stdin();
    let mut stdout = io::BufWriter::new(io::stdout().lock());
    for line in stdin.lock().lines() {
        let line = line?;
        let reply = match serde_json::from_str::<Command>(&line) {
            Ok(command) => { event_queue.roundtrip(&mut app)?; app.handle(command) }
            Err(error) => Reply { ok: false, error: Some(format!("invalid JSON: {error}")), result: None },
        };
        serde_json::to_writer(&mut stdout, &reply)?;
        stdout.write_all(b"\n")?;
        stdout.flush()?;
    }
    Ok(())
}
