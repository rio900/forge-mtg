import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.scenes.scene2d.ui.TextField;
import com.badlogic.gdx.utils.Array;
import forge.Forge;
import forge.adventure.scene.*;
import forge.adventure.util.*;
import forge.adventure.world.WorldSave;
import java.nio.file.Path;
import java.util.Set;
import java.util.concurrent.*;
import java.util.function.BooleanSupplier;

public class AvatarMenuProbe {
    static <T> T ui(Callable<T> task) throws Exception {
        var future = new FutureTask<>(task);
        Gdx.app.postRunnable(future);
        return future.get(120, TimeUnit.SECONDS);
    }
    static void until(BooleanSupplier condition, String step) throws Exception {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(180);
        while (!condition.getAsBoolean()) {
            if (System.nanoTime() >= deadline) throw new AssertionError(step + ": " + Forge.getCurrentScene());
            Thread.sleep(250);
        }
    }
    static Object field(NewGameScene scene, String name) throws Exception {
        var f = NewGameScene.class.getDeclaredField(name);
        f.setAccessible(true);
        return f.get(scene);
    }
    static void test() throws Exception {
        until(() -> Forge.afterDBloaded || Forge.getCurrentScene() != null, "startup");
        if (Forge.getCurrentScene() == null) ui(() -> { Forge.openAdventure(); return null; });
        until(() -> Forge.getCurrentScene() instanceof StartScene, "main menu");
        var profile = Path.of("").toRealPath();
        var save = Path.of(WorldSave.getSaveDir()).toFile().getCanonicalFile().toPath();
        if (!Config.instance().getPlane().equals("AvatarEdited") ||
                !save.startsWith(profile))
            throw new AssertionError("Unexpected " + Config.instance().getPlane() + " save " + save + " for " + profile);
        ui(() -> StartScene.instance().NewGame());
        until(() -> Forge.getCurrentScene() instanceof NewGameScene, "new game");
        ui(() -> {
            var scene = NewGameScene.instance();
            ((TextField)field(scene,"selectedName")).setText("Avatar Chaos Test");
            var modes = (Array<?>)field(scene,"modes");
            for (int i = 0; i < modes.size; i++) {
                if (modes.get(i) == AdventureModes.Chaos) {
                    ((Selector)field(scene,"mode")).setCurrentIndex(i);
                    return scene.start();
                }
            }
            throw new AssertionError("Chaos unavailable in menu");
        });
        until(() -> Forge.getCurrentScene() instanceof GameScene || Forge.getCurrentScene() instanceof TileMapScene, "world");
        ui(() -> {
            var active = WorldSave.getCurrentSave().getPlayer().getSelectedDeck();
            var allowed = Set.of(Config.instance().getConfigData().allowedEditions);
            AvatarStarters.validate("menu/" + active.getName(), active, allowed);
            if (!active.getName().startsWith("Avatar Pile ")) throw new AssertionError(active.getName());
            var totals = new java.util.TreeMap<String,Integer>();
            for (var row : active.getMain()) totals.merge(row.getKey().getEdition(),row.getValue(),Integer::sum);
            System.out.println("PASS GUI Chaos active deck " + active.getName() + " cards=60 " + totals);
            return null;
        });
    }
    public static void main(String[] args) throws Exception {
        TestProfile.require();
        new Thread(() -> {
            try { test(); System.exit(0); }
            catch (Throwable ex) { ex.printStackTrace(); System.exit(1); }
        },"Avatar menu check").start();
        forge.app.Main.main(args);
    }
}
