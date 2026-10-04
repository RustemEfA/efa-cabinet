// EfA → Sila Union: построение модели BPMN 2.0 из описания процесса.
// Сгенерировано efa_bpmn_generator.py. Запускать на папке или базе данных:
// в ней будет создана папка «EfA — <название процесса>» с моделью и объектами.
// Скрипт не привязан к конкретной базе: его можно передать в любую инсталляцию Sila Union
// (методология базы — «Стандартный пресет»). Запуск: правой кнопкой мыши на базе/папке → Скрипт → Запустить скрипт.

import ru.nextconsulting.bpm.dto.NodeId
import ru.nextconsulting.bpm.repository.structure.NodeType
import ru.nextconsulting.bpm.script.repository.TreeRepository
import ru.nextconsulting.bpm.script.tree.elements.Edge
import ru.nextconsulting.bpm.script.tree.elements.ObjectElement
import ru.nextconsulting.bpm.script.tree.node.Model
import ru.nextconsulting.bpm.script.tree.node.ObjectDefinition
import ru.nextconsulting.bpm.scriptengine.context.CustomScriptContext
import ru.nextconsulting.bpm.scriptengine.script.GroovyScript

void execute() {
  Main script = new Main(context: context)
  script.execute()
}

class Main implements GroovyScript {
  CustomScriptContext context

  static final String TITLE = /*TITLE*/
  static final Map POOL = /*POOL*/
  static final String LABEL_STYLE = /*LABEL_STYLE*/
  static final Map TYPES = [
/*TYPES*/
  ]
  static final List ELEMENTS = [
/*ELEMENTS*/
  ]
  static final List EDGES = [
/*EDGES*/
  ]

  @Override
  void setContext(CustomScriptContext context) {
    this.context = context
  }

  @Override
  void execute() {
    TreeRepository repository = context.createTreeRepository(false)

    // Строим в базе или папке, на которой запустили скрипт.
    NodeId startId = context.nodeId()
    def parent = startId != null ? repository.read(startId) : null
    if (parent == null || !(parent.isFolder() || parent.isDb())) {
      throw new RuntimeException('EfA: запустите скрипт на базе данных или папке, где нужно построить процесс: ' +
          'в навигаторе правой кнопкой мыши на базе/папке → Скрипт → Запустить скрипт. ' +
          'Методология базы должна быть «Стандартный пресет».')
    }

    def folder = repository.create(parent, NodeType.FOLDER, 'EfA — ' + TITLE)
    repository.update(folder)

    Model model = repository.create(folder, NodeType.MODEL, TITLE)
    model.setModelTypeId(/*MODEL_TYPE*/)
    repository.update(model)
    model = repository.read(model)

    // Определения объектов: одно на каждое уникальное имя и тип
    Map<String, ObjectDefinition> defs = [:]
    def definition = { String kind, String name ->
      String key = kind + '|' + name
      if (!defs.containsKey(key)) {
        ObjectDefinition d = repository.create(folder, NodeType.OBJECT, name)
        d.setObjectTypeId(TYPES[kind][0] as String)
        repository.update(d)
        defs[key] = d
      }
      return defs[key]
    }

    def place = { ObjectElement el, String kind, Map g ->
      el.setSymbolId(TYPES[kind][1] as String)
      el.setX(g.x as Double)
      el.setY(g.y as Double)
      el.setWidth(g.w as Double)
      el.setHeight(g.h as Double)
      if (g.lw) {   // у пула, дорожек и шлюзов без названия подписи нет
        // Стиль фигуры не трогаем: в нём Sila хранит графику символа (круг, ромб, документ).
        el.setLabelStyle(LABEL_STYLE)
        el.setLabelWidth(g.lw as Double)
        el.setLabelHeight(g.lh as Double)
        el.setLabelXOffset(g.lx as Double)
        el.setLabelYOffset(g.ly as Double)
      }
      return el
    }

    Map<String, ObjectElement> els = [:]
    ObjectElement poolEl = place(model.createObjectElement(definition('pool', POOL.name as String)), 'pool', POOL)

    ELEMENTS.findAll { it.kind == 'lane' }.each { g ->
      els[g.id as String] = place(model.createObjectElement(definition('lane', g.name as String), poolEl), 'lane', g)
    }
    ELEMENTS.findAll { it.kind != 'lane' }.each { g ->
      String name = (g.name as String) ?: ' '
      els[g.id as String] = place(model.createObjectElement(definition(g.kind as String, name), els[g.lane as String]), g.kind as String, g)
    }

    EDGES.each { e ->
      Edge edge = model.createEdge(els[e.from as String], els[e.to as String])
      edge.setEdgeTypeId(e.type as String)
      if (e.name) {
        edge.setName(e.name as String)
      }
      edge.setStyle(e.style as String)
      // Контейнер связи — ближайший общий родитель источника и цели: дорожка, если обе
      // фигуры в одной дорожке, иначе пул. Точки изгиба Sila Union хранит относительно
      // этого контейнера, а в данных они абсолютные — пересчитываем.
      def ancestors = []
      def a = els[e.from as String].getParent()
      while (a != null) { ancestors << a; a = a.getParent() }
      def lca = els[e.to as String].getParent()
      while (lca != null && !ancestors.any { it.equalsIds(lca) }) { lca = lca.getParent() }
      if (lca != null) {
        edge.setParent(lca)
      }
      double ox = 0d, oy = 0d
      def p = lca
      while (p != null) {
        ox += (p.getX() ?: 0d) as double
        oy += (p.getY() ?: 0d) as double
        p = p.getParent()
      }
      (e.wp as List).eachWithIndex { pt, i ->
        edge.addWaypoint(i, ((pt[0] as double) - ox) as Double, ((pt[1] as double) - oy) as Double)
      }
    }

    repository.update(model)
  }
}
